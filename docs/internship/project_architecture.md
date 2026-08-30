# NetSage AI — Technical Project Architecture

This document provides a detailed architectural specification for **NetSage AI**, detailing component responsibilities, data flow specifications, state persistence models, and safety guarantees.

---

## 1. Architectural Overview

NetSage AI is built around a **hybrid diagnosis paradigm**:

```
+-----------------------------------------------------------------------------------+
|                                  INPUT LAYER                                      |
|   Symptom Description + Topology Note + Raw Cisco "show" Command Outputs           |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                 DATA LOAD LAYER                                   |
|   src/case_loader.py (Loads data/sample_cases.json or data/cases.csv)             |
+-----------------------------------------------------------------------------------+
                                         |
                         +---------------+---------------+
                         |                               |
                         v                               v
+-----------------------------------+   +-----------------------------------+
|      DETERMINISTIC RULE ENGINE    |   |         AI DIAGNOSER ENGINE       |
|    src/rule_checker.py            |   |    src/ai_diagnoser.py            |
|  - 12 regex/text checks           |   |  - Mock Mode (Offline default)    |
|  - 100% reproducible              |   |  - Live Mode (Anthropic SDK)      |
|  - No API key / No LLM            |   |  - Structured JSON Schema         |
|  - Output: FAIL/WARN/PASS         |   |  - Raw Line Evidence Citation     |
+-----------------------------------+   +-----------------------------------+
                         |                               |
                         +---------------+---------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            EVIDENCE COMPARISON & CORROBORATION                    |
|   src/main.py (Corroborates rule findings with AI diagnosis, evaluates match)      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            MANDATORY HUMAN REVIEW LAYER                           |
|   src/human_review.py (Requires ACCEPT / EDIT / REJECT decision)                 |
|   - Re-prompts on invalid input; forces corrected diagnosis for EDIT/REJECT       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            STATE PERSISTENCE & ANALYTICS                          |
|   - outputs/review_log.json (Persists all human review decisions & final root cause) |
|   - outputs/sample_diagnoses.json (Persists batch evaluation outputs)             |
|   - data/responsible_ai_log.csv (Stores 5 documented AI correction examples)      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            PRESENTATION & REPORTING LAYER                         |
|   - src/dashboard.py (5-tab Streamlit dashboard: Overview, Categories,            |
|                        Severity, Responsible AI, Case Detail)                     |
|   - src/main.py (CLI interface: --list, --case, --demo, --batch)                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Component Specifications

### 2.1 Case Loader (`src/case_loader.py`)
* **Responsibility:** Loads case definitions from `data/sample_cases.json` (canonical nested JSON format) or `data/cases.csv` (flattened CSV fallback).
* **Key Functions:**
  * `load_cases()`: Loads and parses dataset items.
  * `get_case_by_id(case_id, cases)`: Returns specific case dictionary by `case_id`.
  * `filter_cases(cases, category, severity)`: Exact filtering by explicit `category` field or `severity`.
  * `dataset_summary(cases)`: Computes exact non-overlapping category and severity distributions.

### 2.2 Deterministic Rule Checker (`src/rule_checker.py`)
* **Responsibility:** Performs static analysis over raw text command output in `show_outputs`.
* **Execution Model:** 100% deterministic, zero LLM calls, zero network overhead.
* **12 Check Implementations:**
  1. `check_duplicate_ip`: Re-assigns same IP to multiple hosts.
  2. `check_wrong_subnet_mask`: Mask disagreement on same `/24` subnet.
  3. `check_gateway_mismatch`: Gateway IP not found on any router interface.
  4. `check_interface_down`: Interface `administratively down`, `down/down`, or `err-disabled`.
  5. `check_missing_vlan`: Switchport VLAN missing from `show vlan brief`.
  6. `check_missing_route`: Unadvertised or missing routing table entry.
  7. `check_trunk_mismatch`: Pruned VLAN or unformed 802.1q trunk.
  8. `check_missing_dhcp_pool`: Router interface subnet without matching DHCP pool.
  9. `check_incorrect_dhcp_network`: Pool `default-router` outside pool subnet.
  10. `check_acl_blocking`: Explicit `deny` blocking target subnet.
  11. `check_nat_missing`: `ip nat inside/outside` interface markings absent.
  12. `check_nat_translation_absent`: `Total active translations: 0`.

### 2.3 AI Diagnoser Engine (`src/ai_diagnoser.py`)
* **Responsibility:** Evidence reasoning and root cause diagnosis generation.
* **Dual Execution Modes:**
  * **Mock Mode (`MOCK_MODE=true`):** Offline execution returning evidence-grounded diagnoses. Uses exact raw line citations from `show_outputs` for normal cases, and deliberate mistake definitions (`KNOWN_AI_MISTAKES`) for Responsible AI cases.
  * **Live Mode (`MOCK_MODE=false`):** Invokes Anthropic API (`claude-sonnet-4-6`) using system prompt ([prompts/diagnose_prompt.md](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/prompts/diagnose_prompt.md)) and worked few-shot examples ([prompts/few_shot_examples.md](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/prompts/few_shot_examples.md)).
* **Fallback Guarantee:** `_fallback_diagnosis()` handles missing API keys, API errors, JSON parse failures, and timeouts gracefully.

### 2.4 Human Review Pipeline (`src/human_review.py`)
* **Responsibility:** Governs the human decision loop.
* **Validation Logic:**
  * Requires decision in `{"ACCEPT", "EDIT", "REJECT"}`.
  * Rejects `EDIT` or `REJECT` choices if `corrected_diagnosis` is missing or blank.
  * Saves review state to `outputs/review_log.json`.

### 2.5 Presentation Layer (`src/main.py` & `src/dashboard.py`)
* **CLI (`main.py`):** Multi-mode command line interface supporting single case analysis (`--case`), guided interactive demo (`--demo`), dataset listing (`--list`), and batch evaluation (`--batch`).
* **Dashboard (`dashboard.py`):** 5-tab Streamlit web application providing high-level metrics, category charts, severity distribution, Responsible AI audit tables, and case details.

---

## 3. Data Safety & Governance Guarantees

1. **Hardcoded Human Review Flag:** `needs_human_review` is explicitly set to `True` on every returned diagnosis object.
2. **Read-Only Operation:** NetSage AI never issues configuration commands to devices. All `fix_steps` are framed as recommendations for human execution.
3. **Persisted Oversight:** All human reviewer decisions, timestamps, reviewer names, original AI diagnoses, and corrected diagnoses are permanently logged.
