# NetSage AI — User Manual & Operations Guide

This document provides a step-by-step user manual for installing, configuring, running, and navigating **NetSage AI** across both Command-Line (CLI) and Web Dashboard interfaces.

---

## 1. Prerequisites & Environment Setup

### System Requirements
* **Operating System:** Windows 10/11, Linux, or macOS.
* **Python:** Python 3.10 or higher (Python 3.13 recommended).
* **Terminal Shell:** PowerShell, Bash, or Zsh.

### Step 1: Clone or Navigate to Project Folder
```bash
cd netsage-ai
```

### Step 2: Create a Project-Local Virtual Environment
```bash
# Windows
python -m venv .venv

# Linux / macOS
python3 -m venv .venv
```

### Step 3: Activate the Virtual Environment
```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.\.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 2. Command-Line Interface (CLI) Guide

All CLI operations are driven by `src/main.py`.

### 2.1 List All Troubleshooting Cases
Lists all 35 cases with severity badges and symptoms:
```bash
python src/main.py --list
```
*Sample Output:*
```text
CASE-001   [Medium  ] PC-A (VLAN 10, Sales) cannot ping PC-B (VLAN 10, Sales)...
CASE-002   [High    ] All hosts on VLAN 30 (Server farm) lost connectivity...
CASE-025   [High    ] PC gets an IP address and can ping its gateway...
```

### 2.2 Run Guided Demo Mode (`CASE-025`)
Runs the complete 5-step analysis pipeline for `CASE-025` (ACL blocking server subnet):
```bash
python src/main.py --demo
```

### 2.3 Analyze and Review a Specific Case
Runs the pipeline for a specific `case_id` with interactive human review prompts:
```bash
python src/main.py --case CASE-007
```

**Interactive Review Prompt Options:**
* Type `A` (or `ACCEPT`): Accepts the AI diagnosis.
* Type `E` (or `EDIT`): Edits the AI diagnosis. Prompts for:
  1. *Corrected diagnosis* (required).
  2. *Reason for correction* (recommended).
  3. *Reviewer comments* (optional).
* Type `R` (or `REJECT`): Rejects the AI diagnosis. Prompts for required corrected diagnosis.

### 2.4 Run Non-Interactive Batch Evaluation
Evaluates all 35 cases in mock mode and writes output JSON to `outputs/sample_diagnoses.json`:
```bash
python src/main.py --batch
```

---

## 3. Streamlit Web Dashboard Guide

Launch the Streamlit dashboard:
```bash
python -m streamlit run src/dashboard.py
```
*Access URL:* Open `http://localhost:8501` in Chrome or any modern browser.

### 3.1 Overview Tab
* Displays overall system metrics: Total Cases (35), Cases Diagnosed (35), Accepted Count (30), Edited Count (5), Rejected Count (0), and AI-Human Agreement Rate (`85.7%`).
* Indicates active diagnoser mode (`MOCK` vs `LIVE`).

### 3.2 Issue Analysis Tab
* Displays an interactive bar chart and data table breaking down case counts across the 8 canonical categories: VLAN (5), Gateway (4), DHCP (5), DNS (4), Routing (5), ACL (4), NAT (4), Wireless (4).

### 3.3 Severity Breakdown Tab
* Displays a bar chart ordered by severity level: Low (4), Medium (10), High (17), Critical (4).

### 3.4 Responsible AI Tab
* Displays the **Human Correction Rate** metric (`14.3%`).
* Renders an interactive table of the 5 documented AI correction cases (`CASE-004`, `CASE-008`, `CASE-012`, `CASE-025`, `CASE-028`) detailing original AI error, human correction, reason, and lesson learned.

### 3.5 Case Detail Tab (Inspector View)
1. Select any case from the dropdown menu (e.g. `CASE-025`).
2. **Left Column:** Displays Reported Symptom, Topology Note, and Collapsible Show Command Evidence code blocks.
3. **Right Column:** Displays Rule Checker Findings (`[WARN] acl_blocking`), AI Diagnosis (Root cause, Confidence %, OSI layer, Next command, Evidence cited, Fix steps), and Persisted Human Review Status.

---

## 4. Live Anthropic LLM API Setup (Optional)

By default, NetSage AI operates in **offline mock mode** (`MOCK_MODE=true`). To enable live Anthropic Claude API calls:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and set:
   ```env
   MOCK_MODE=false
   ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here
   ```
3. Export `.env` variables or pass them in your terminal session before launching `main.py` or `dashboard.py`.

*Note: If `MOCK_MODE=false` is set without an API key, `ai_diagnoser.py` returns a graceful error fallback (`confidence: 0`, `needs_human_review: true`) without crashing.*

---

## 5. Running Automated Unit Tests

Execute the complete 45-test suite:
```bash
python -m pytest tests/ -v
```
Alternatively, run test files individually:
```bash
python tests/test_cases.py
python tests/test_rule_checker.py
python tests/test_ai_diagnoser.py
```
