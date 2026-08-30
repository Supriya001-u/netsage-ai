# NetSage AI — Interactive Demonstration & Viva Walkthrough Script

This script provides a timed, step-by-step presentation outline for demonstrating **NetSage AI** during an internship evaluation, viva, or live project review.

---

## Demonstration Overview

* **Target Duration:** 8 to 10 minutes
* **Primary Case:** `CASE-025` (High Severity ACL blocking server traffic)
* **Secondary Cases:** `CASE-004`, `CASE-008`, `CASE-012`, `CASE-028` (Responsible AI human corrections)
* **Tools Required:** Terminal window + Web Browser (`http://localhost:8501`)

---

## Step 1: Introduction & Problem Context (1 Minute)

**Presenter Script:**
> *"Good morning/afternoon. Today I am presenting **NetSage AI**, an AI-assisted network fault diagnosis platform with deterministic validation and mandatory human-in-the-loop review.
>
> When troubleshooting lab networks, junior engineers often struggle to correlate broad symptoms with raw `show` command outputs. Pure AI models can hallucinate evidence or claim autonomous fix execution. NetSage AI fixes this by using a dual-engine approach: a 12-check deterministic rule checker combined with an evidence-grounded AI diagnoser. Crucially, NetSage AI is safe by construction: no fix is ever auto-applied, and every single diagnosis requires human review."*

---

## Step 2: CLI Demonstration — Case CASE-025 (3 Minutes)

### Action 1: List Dataset
Run in terminal:
```bash
python src/main.py --list
```
**Explain:** Show the 35 cases categorized across VLAN, Gateway, DHCP, DNS, Routing, ACL, NAT, and Wireless.

### Action 2: Execute Demo Mode
Run in terminal:
```bash
python src/main.py --demo
```

### Walkthrough of Output Steps

1. **Case & Evidence Display:**
   Point out the symptom: *"PC cannot reach file server SVR1 (192.168.30.50) in VLAN 30"*.
   Point out the show output: `show access-lists` displaying line 20: `deny ip 192.168.10.0 0.0.0.255 host 192.168.30.50`.

2. **STEP 1 — Deterministic Rule Checker:**
   Point out: `[WARN] acl_blocking (severity: High)`. The rule checker immediately catches the explicit deny statement without needing AI.

3. **STEP 2 — AI Diagnosis (Mock Mode):**
   Point out AI root cause: *"R1's routing table is missing a route to the 192.168.30.0/24 server subnet"* (`64%` confidence).

4. **STEP 3 — Evidence Comparison:**
   Point out: `Exact match with dataset: False`.
   **Explain:** *"Here the AI suggested a plausible routing explanation, but the ground truth evidence shows an explicit ACL deny. This demonstrates exactly why human review is mandatory!"*

5. **STEP 4 — Human Review Prompt:**
   Enter `E` (Edit).
   Enter corrected diagnosis: `"ACL entry 20 explicitly denies traffic from 192.168.10.0/24 to host 192.168.30.50"`.
   Enter reason: `"show access-lists line 20 explicitly denies source subnet 192.168.10.0/24"`.

6. **STEP 5 — Final Diagnosis & Persistence:**
   Point out: Review decision `EDIT` is saved to `outputs/review_log.json`.

---

## Step 3: Streamlit Dashboard Walkthrough (3 Minutes)

Open browser at `http://localhost:8501`.

### Tab 1: Overview Tab
* Point out top metrics: **Total Cases (35)**, **Diagnosed Cases (35)**, **Accepted (30)**, **Edited (5)**, **AI-Human Agreement (85.7%)**.
* Point out active mode: `MOCK (no API key required)`.

### Tab 2: Issue Analysis Tab
* Point out the category distribution chart: 5 VLAN, 4 Gateway, 5 DHCP, 4 DNS, 5 Routing, 4 ACL, 4 NAT, 4 Wireless = 35 total cases.

### Tab 3: Severity Breakdown Tab
* Point out the severity distribution: Low (4), Medium (10), High (17), Critical (4).

### Tab 4: Responsible AI Tab
* Point out **Human Correction Rate (`14.3%`)**.
* Highlight the 5 documented mistake cases (`CASE-004`, `CASE-008`, `CASE-012`, `CASE-025`, `CASE-028`) in the data table.
* **Explain:** *"These 5 cases demonstrate real scenarios where the AI's initial guess was corrected by human engineers — providing empirical proof for why human review is required."*

### Tab 5: Case Detail Tab
* Select `CASE-025` from the dropdown.
* Demonstrate split inspector: Left side shows raw CLI outputs; Right side shows Rule Checker findings (`acl_blocking`), AI diagnosis (`64%` confidence), and persisted Human Review decision (`EDIT`).

---

## Step 4: Verification & Test Suite Execution (1 Minute)

Run in terminal:
```bash
python -m pytest tests/ -v
```
**Explain:** Show that all 45 automated unit tests pass in 0.49 seconds, covering dataset schema, rule checker logic, AI diagnoser behavior, raw evidence grounding, and Responsible AI logging.

---

## Step 5: Summary & Conclusion (1 Minute)

**Presenter Script:**
> *"In summary, NetSage AI achieves complete, reliable lab network troubleshooting by grounding AI diagnoses in raw CLI evidence, catching structural errors with 12 deterministic rules, and enforcing human-in-the-loop review on every single case. Thank you, and I am open to any questions."*
