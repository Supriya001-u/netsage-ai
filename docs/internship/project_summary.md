# Project Summary Document: NetSage AI

**Project Title:** NetSage AI — AI-Assisted Network Fault Diagnosis with Deterministic Validation and Mandatory Human-in-the-Loop Review  
**Host Organization:** Cisco Systems, Inc.  
**Department:** Network Systems & Artificial Intelligence  
**Role:** AI / Network Automation Intern  
**Project Duration:** Internship Term 2026  
**Environment:** Python 3.13.5 | Streamlit 1.62.0 | Anthropic SDK 1.2.0 | pytest 9.1.1  
**GitHub Repositories:**  
- Primary: [https://github.com/Supriya001-u/netsage-ai](https://github.com/Supriya001-u/netsage-ai)  
- Secondary: [https://github.com/Supriya0-0/Supriya-netsage-ai](https://github.com/Supriya0-0/Supriya-netsage-ai)  

---

## Executive Summary

Junior network engineers and students working with Cisco Packet Tracer, GNS3, or enterprise lab environments frequently face challenges diagnosing multi-layer network anomalies. Correlating raw `show` command outputs, topology specifications, and protocol behaviors across Layer 1 through Layer 7 requires substantial experience and manually sifting through high volumes of CLI output.

**NetSage AI** addresses this challenge by combining a 12-check **deterministic Python rule engine** with an **evidence-grounded AI diagnoser** and a **mandatory human-in-the-loop review workflow**. The system processes natural language symptoms, topology notes, and raw command evidence to generate structured JSON diagnoses containing root causes, confidence scores, OSI layer classifications, recommended next commands, and fix steps.

Crucially, NetSage AI is **safe by construction**: no AI recommendation is ever automatically applied to a network device, and every diagnosis requires explicit human review (`ACCEPT`, `EDIT`, or `REJECT`). The project includes 35 comprehensive troubleshooting cases across 8 canonical fault categories, 5 documented Responsible AI correction cases where human review catches and corrects AI misdiagnoses, a 5-tab Streamlit dashboard, a complete CLI pipeline, and a 45/45 passing unit test suite.

---

## Key System Highlights

### 1. Dual-Engine Architecture
* **Deterministic Rule Checker (`src/rule_checker.py`)**: 12 non-AI regex and IP arithmetic checks for structural errors (subnet mask mismatches, duplicate IPs, missing default routes, trunking errors, ACL explicit denies, interface admin down state, missing DHCP pools, and NAT misconfigurations). Requires zero API keys or external services.
* **Evidence-Grounded AI Engine (`src/ai_diagnoser.py`)**: Generates structured JSON diagnoses. Operates in offline **Mock Mode** (default) or live **Anthropic LLM Mode**. Mandates exact citations of raw `show` command output lines.

### 2. Human-in-the-Loop Governance
* Every diagnosis is held in a draft state until an engineer selects `ACCEPT`, `EDIT`, or `REJECT`.
* Reviewer decisions, modifications, and timestamps are persisted to `outputs/review_log.json`.

### 3. Responsible AI Audit Framework (`data/responsible_ai_log.csv`)
* Explicitly logs 5 real scenarios where the AI model generates plausible-but-incorrect diagnoses (e.g., confusing physical interface state with VLAN pruning, misattributing ACL rule numbers, or hallucinating gateway subnets).
* Documents how human review catches and corrects each AI mistake, demonstrating responsible AI deployment.

### 4. 5-Tab Streamlit Dashboard (`src/dashboard.py`)
* **Overview**: High-level KPIs, AI confidence distributions, and human agreement rates.
* **Case Inspector**: Full deep-dive into raw `show` outputs, rule findings, AI JSON diagnosis, and review controls for all 35 cases.
* **Severity Breakdown**: Visual chart analysis by issue severity (Low, Medium, High, Critical).
* **Issue Analysis**: Distribution breakdown across all 8 Cisco fault categories.
* **Responsible AI Panel**: Transparent audit log highlighting AI misdiagnoses and human corrections.

### 5. Automated Verification Suite (`tests/`)
* **45/45 Unit Tests Passed** across 3 test modules:
  * `test_rule_checker.py` (23 tests): Positive and negative test cases for all 12 deterministic checks.
  * `test_cases.py` (10 tests): Dataset schema, uniqueness, severity, and fault distribution validity.
  * `test_ai_diagnoser.py` (12 tests): Schema validation, confidence calibration, and Responsible AI log integrity.

---

## Dataset & Fault Category Coverage

| Category | Cases Count | Primary Cisco Commands Parsed |
| :--- | :---: | :--- |
| **VLAN & Trunking** | 5 | `show vlan brief`, `show interfaces trunk` |
| **Gateway & Subnetting** | 5 | `show ip interface brief`, `show running-config` |
| **DHCP Configuration** | 4 | `show ip dhcp pool`, `show ip dhcp binding` |
| **DNS Resolution** | 4 | `show hosts`, `show running-config` |
| **Routing (Static/OSPF)** | 5 | `show ip route`, `show ip ospf neighbor` |
| **Access Control Lists (ACL)**| 4 | `show access-lists`, `show ip interface` |
| **Network Address Translation (NAT)**| 4 | `show ip nat translations`, `show ip nat statistics` |
| **Wireless LAN (WLAN)** | 4 | `show wlan summary`, `show ip interface brief` |
| **Total** | **35 Cases** | **Comprehensive Multi-Layer Evidence** |

---

## Project Deliverables & Submission Files

1. **Solution ZIP Archive**: [`NetSage_AI_Solution_Package.zip`](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/NetSage_AI_Solution_Package.zip)
2. **Internship Final Report**: [`docs/internship/internship_report.md`](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/docs/internship/internship_report.md)
3. **Project Architecture Spec**: [`docs/internship/project_architecture.md`](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/docs/internship/project_architecture.md)
4. **Testing & Validation Report**: [`docs/internship/testing_and_validation.md`](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/docs/internship/testing_and_validation.md)
5. **User Manual**: [`docs/internship/user_manual.md`](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/docs/internship/user_manual.md)
6. **Demo Script**: [`docs/internship/demo_script.md`](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/docs/internship/demo_script.md)

---

## Quick Start Commands

```powershell
# 1. Run full test suite (45 passed)
python -m pytest tests/ -v

# 2. Run CLI interactive guided demo
python src/main.py --demo

# 3. Launch Streamlit Web Dashboard
streamlit run src/dashboard.py
```
