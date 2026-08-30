# NetSage AI — Module Description Document

This document provides a line-item reference for all source code modules within `src/`, detailing function signatures, inputs, outputs, logic flow, and error handling.

---

## 1. Module: `src/case_loader.py`

**Purpose:** Manages dataset ingestion, filtering, and summary statistics.

### Functions & Interfaces

#### `load_cases()`
* **Parameters:** None.
* **Returns:** `list` of `dict` case objects.
* **Logic:** Prefers `data/sample_cases.json`. If missing, falls back to reading `data/cases.csv` and deserializing JSON string `show_outputs`.
* **Exceptions:** Raises `FileNotFoundError` if neither dataset file exists.

#### `get_case_by_id(case_id, cases=None)`
* **Parameters:** `case_id` (`str`), `cases` (`list`, optional).
* **Returns:** `dict` matching case object or `None`.

#### `filter_cases(cases=None, category=None, severity=None)`
* **Parameters:** `cases` (`list`, optional), `category` (`str`, optional), `severity` (`str`, optional).
* **Returns:** Filtered `list` of case objects.
* **Logic:** Matches case-insensitive exact string against explicit `category` field (avoiding fuzzy keyword double-counting) and `severity`.

#### `dataset_summary(cases=None)`
* **Parameters:** `cases` (`list`, optional).
* **Returns:** `dict` containing:
  * `total_cases`: `int` (35)
  * `by_category`: `dict` mapping each of the 8 canonical categories to exact count.
  * `by_severity`: `dict` mapping severity levels to exact count.

---

## 2. Module: `src/rule_checker.py`

**Purpose:** Implements 12 non-AI deterministic rule checks over raw CLI text.

### Functions & Interfaces

#### `_finding(check, status, severity, evidence, message)`
* **Helper:** Constructs standard finding dictionary containing `check`, `status` (`PASS`/`WARN`/`FAIL`), `severity`, `evidence`, and `message`.

#### Individual Check Functions
* `check_duplicate_ip(show_outputs)`
* `check_wrong_subnet_mask(show_outputs)`
* `check_gateway_mismatch(show_outputs)`
* `check_interface_down(show_outputs)`
* `check_missing_vlan(show_outputs)`
* `check_missing_route(show_outputs)`
* `check_trunk_mismatch(show_outputs)`
* `check_missing_dhcp_pool(show_outputs)`
* `check_incorrect_dhcp_network(show_outputs)`
* `check_acl_blocking(show_outputs)`
* `check_nat_missing(show_outputs)`
* `check_nat_translation_absent(show_outputs)`

#### `run_all_checks(case)`
* **Parameters:** `case` (`dict` or `show_outputs` dict).
* **Returns:** `list` of 12 finding dictionaries.

#### `failing_findings(case)`
* **Parameters:** `case` (`dict`).
* **Returns:** `list` of findings where `status` is `FAIL` or `WARN`.

---

## 3. Module: `src/ai_diagnoser.py`

**Purpose:** Encapsulates AI/LLM diagnosis generation (Offline Mock & Live Anthropic API).

### Key Variables & Constants
* `MOCK_MODE`: Environment boolean (defaults to `True`).
* `ANTHROPIC_MODEL`: `"claude-sonnet-4-6"`.
* `KNOWN_AI_MISTAKES`: Dictionary of 5 deliberate mistake cases (`CASE-004`, `CASE-008`, `CASE-012`, `CASE-025`, `CASE-028`).

### Functions & Interfaces

#### `_pick_evidence_lines(case, n=2)`
* **Logic:** Scans raw `show_outputs` lines for key fault patterns (`err-disabled`, `administratively down`, `default-router`, `Default Gateway`, `is not advertised`, `deny`, `Total active translations`, `Vlans allowed on trunk`, `ip nat inside`, etc.) and extracts literal raw lines from `show_outputs`.

#### `_build_mock_diagnosis(case, rule_findings)`
* **Logic:** 
  * If `case_id` is in `KNOWN_AI_MISTAKES`, returns the simulated wrong diagnosis object.
  * Otherwise, uses `expected_fault` as root cause, sets confidence (`88%-96%` if rules fire, `68%` if no rules fire), populates `evidence` using `_pick_evidence_lines(case)`, attaches category fix steps, and sets `needs_human_review = True`.

#### `_live_diagnose(case, rule_findings)`
* **Logic:** Imports `anthropic` SDK dynamically, loads `prompts/diagnose_prompt.md` and `prompts/few_shot_examples.md`, sends prompt to Anthropic API, parses JSON response, and sets `needs_human_review = True`.

#### `_fallback_diagnosis(case, error)`
* **Logic:** Catches live-mode errors (missing API key, network timeout, API error, malformed JSON) and returns graceful fallback diagnosis object (`confidence: 0`, `needs_human_review: True`).

#### `diagnose(case, rule_findings=None)`
* **Main Entry Point:** Invokes `_mock_diagnose` or `_live_diagnose` with fallback, verifies all required keys exist, and returns final diagnosis object.

---

## 4. Module: `src/human_review.py`

**Purpose:** Manages human review recording, validation, and analytics.

### Functions & Interfaces

#### `load_reviews()`
* **Returns:** `list` of persisted review entries from `outputs/review_log.json`. Returns `[]` if log file does not exist yet.

#### `save_review(case_id, ai_diagnosis, reviewer_decision, corrected_diagnosis=None, reviewer_comments=None, reason_for_correction=None, reviewer_name="viva_demo_user")`
* **Logic:** Validates `reviewer_decision` in `{"ACCEPT", "EDIT", "REJECT"}`. Enforces `corrected_diagnosis` for `EDIT`/`REJECT`. Replaces any prior entry for `case_id` and saves updated list to `outputs/review_log.json`.
* **Exceptions:** Raises `ValueError` on invalid decision or missing required correction text.

#### `agreement_rate(reviews=None)`
* **Returns:** `float` percentage of `ACCEPT` decisions over total reviews (e.g., `85.7%`).

#### `review_counts(reviews=None)`
* **Returns:** `dict` with counts for `ACCEPT`, `EDIT`, `REJECT`.

---

## 5. Module: `src/main.py`

**Purpose:** CLI pipeline entry point supporting `--list`, `--case`, `--demo`, and `--batch`.

### Core Pipeline Steps (`run_pipeline(case, interactive=True)`)
1. **Show Case:** Prints symptom, topology note, and formatted show command outputs.
2. **Step 1 (Deterministic Rule Checker):** Executes `run_all_checks()` and prints findings.
3. **Step 2 (AI Diagnosis):** Executes `diagnose()` and prints root cause, confidence, OSI layer, evidence, next command, and fix steps.
4. **Step 3 (Evidence Comparison):** Compares AI root cause against dataset `expected_fault` and prints match result.
5. **Step 4 (Human Review):** Prompts user for `A` (Accept), `E` (Edit), or `R` (Reject). Collects corrected diagnosis and reason on `E`/`R`.
6. **Step 5 (Final Diagnosis):** Displays final agreed diagnosis and persists review entry to `outputs/review_log.json`.

---

## 6. Module: `src/dashboard.py`

**Purpose:** Streamlit Web Application (5 Tabs).

### Tab Renderers
* `render_overview(cases, reviews)`: Displays top metric cards (Total Cases, Diagnosed Count, Accept/Edit/Reject Counts, Agreement Rate).
* `render_issue_analysis(cases)`: Displays category bar chart and dataframe.
* `render_severity(cases)`: Displays severity breakdown bar chart.
* `render_responsible_ai(reviews)`: Displays Human Correction Rate metric and `responsible_ai_log.csv` dataframe.
* `render_case_detail(cases, reviews)`: Interactive inspector dropdown for viewing case symptom, topology, evidence code blocks, rule findings, AI diagnosis, and human review status.

---

## 7. Module: `src/utils.py`

**Purpose:** Shared path resolution, JSON I/O, string formatting, and parsing helpers.

* `now_iso()`: Returns current UTC time as ISO-8601 string.
* `load_json(path)` / `save_json(path, data)`: File I/O helpers.
* `strip_code_fences(text)`: Strips markdown ```json fences from LLM responses.
* `safe_json_parse(text, fallback=None)`: Best-effort JSON parser with regex fallback.
* `flatten_show_outputs(show_outputs)`: Formats `{cmd: output}` dictionary into single string.
* `truncate(text, max_len=400)`: String truncation helper.
