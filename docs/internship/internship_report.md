# Internship Final Report: NetSage AI

**Project Title:** NetSage AI — AI-Assisted Network Fault Diagnosis with Deterministic Validation and Mandatory Human-in-the-Loop Review  
**Author:** Technical Engineering Intern  
**Date:** August 2026  
**Environment:** Python 3.13.5 | Streamlit 1.62.0 | Anthropic SDK 1.2.0 | pytest 9.1.1  

---

## Executive Summary

Junior network engineers and students working with Cisco/Packet Tracer lab environments frequently face challenges in diagnosing multi-layer network anomalies. Correlating raw `show` command outputs, topology specifications, and protocol behaviors requires substantial experience. 

**NetSage AI** addresses this gap by combining a 12-check **deterministic Python rule engine** with an **evidence-grounded AI diagnoser** and a **mandatory human-in-the-loop review workflow**. The system processes natural language symptoms, topology notes, and raw command evidence to generate structured JSON diagnoses containing root causes, confidence scores, OSI layer classifications, recommended next commands, and fix steps. 

Crucially, NetSage AI is **safe by construction**: no AI recommendation is ever automatically applied to a network device, and every diagnosis requires explicit human review (`ACCEPT`, `EDIT`, or `REJECT`). The project includes 35 comprehensive troubleshooting cases across 8 canonical fault categories, 5 documented Responsible AI correction cases where human review catches and corrects AI misdiagnoses, a 5-tab Streamlit dashboard, a complete CLI pipeline, and a 45/45 passing unit test suite.

---

## 1. Internship Context & Organization

* **Host Organization:** Cisco Systems, Inc.
* **Department:** Network Systems & Artificial Intelligence
* **Role:** AI / Network Automation Intern
* **Project Duration:** Internship Term 2026
* **Project:** NetSage AI: AI-Assisted Network Troubleshooting Dashboard

---

## 2. Problem Statement

Network troubleshooting in enterprise labs and educational environments (such as Cisco Packet Tracer or GNS3) currently suffers from key operational bottlenecks:

1. **Information Overload:** A single fault can produce voluminous output across multiple `show` commands (`show ip interface brief`, `show running-config`, `show ip route`, `show access-lists`, `show ip nat statistics`, etc.).
2. **Layer Ambiguity:** Behavioral symptoms at Layer 7 (e.g., "cannot open web page") often mask underlying root causes at Layer 1 (cable/interface down), Layer 2 (VLAN pruning / access port misconfiguration), Layer 3 (subnet mask mismatch or missing route), or Layer 4 (ACL deny / NAT port exhaustion).
3. **Over-reliance on Unvalidated AI:** Pure LLM-based diagnosis tools tend to hallucinate evidence, cite nonexistent IP addresses or interfaces, and claim autonomous fix execution without human verification.
4. **Lack of Explainable Rules:** Traditional diagnostic scripts lack structural regex parsing for common configuration errors like IP duplication or subnet mask discrepancies.

---

## 3. Project Objectives

1. **Broad Domain Coverage:** Implement at least 30 (achieved 35) realistic troubleshooting cases covering VLAN, Gateway, DHCP, DNS, Routing, ACL, NAT, and Wireless domains.
2. **Dual-Engine Architecture:** Build a non-AI deterministic rule checker alongside an evidence-grounded AI diagnoser behind a single, unified interface.
3. **Strict Schema & Evidence Grounding:** Enforce structured JSON output for AI diagnoses with mandatory citations of exact lines from raw `show` command outputs.
4. **Mandatory Human-in-the-Loop Review:** Implement an interactive review workflow requiring human engineers to Accept, Edit, or Reject every diagnosis before finalization.
5. **Responsible AI Framework:** Document at least 5 explicit cases where the AI makes plausible-but-wrong diagnoses and a human reviewer corrects them.
6. **Multi-Interface Support:** Provide a 5-tab interactive Streamlit dashboard and a robust CLI pipeline (`--list`, `--case`, `--demo`, `--batch`).
7. **Comprehensive Automated Testing:** Maintain a 100% passing test suite covering dataset integrity, rule checker logic, AI diagnoser behavior, and UI rendering.

---

## 4. Existing System Limitations vs. Proposed NetSage AI Architecture

| Architectural Dimension | Traditional Troubleshooting / Pure LLM | NetSage AI Proposed Solution |
|---|---|---|
| **Structural Error Detection** | Manual comparison or rigid scripts | 12-check deterministic regex rule engine ([rule_checker.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/src/rule_checker.py)) |
| **Reasoning Engine** | Ad-hoc intuition or unconstrained LLM | Dual-engine: Rule Engine + Evidence-Grounded AI Diagnoser ([ai_diagnoser.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/src/ai_diagnoser.py)) |
| **Evidence Citation** | Generic textbook explanations | Mandatory citation of literal raw lines from `show_outputs` |
| **Execution Safety** | Risk of autonomous execution | **Safe by Construction:** `needs_human_review` hardcoded to `True`; zero write access |
| **Human Governance** | Implicit or absent | Explicit `ACCEPT`, `EDIT`, `REJECT` workflow saved to [review_log.json](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/outputs/review_log.json) |
| **AI Error Auditing** | Errors hidden or unmonitored | Responsible AI log ([responsible_ai_log.csv](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/data/responsible_ai_log.csv)) capturing 5 failure modes |

---

## 5. Technology Stack

* **Core Programming Language:** Python 3.13.5
* **Web Dashboard:** Streamlit 1.62.0, pandas 3.0.5, pydeck 0.9.3, Altair 6.2.2
* **LLM Integration:** Anthropic Python SDK (`anthropic` 1.2.0, model `claude-sonnet-4-6`)
* **Testing Framework:** pytest 9.1.1, `streamlit.testing.v1.AppTest`
* **Data Processing & Parsing:** Standard library `re`, `json`, `csv`, `ipaddress`, `argparse`

---

## 6. System Architecture

The high-level pipeline follows a strict, unidirectional flow:

```
INPUT (Symptom + Topology Note + Show Command Evidence)
                   |
                   v
   Case Loader (src/case_loader.py)
                   |
                   v
   Deterministic Rule Checker (src/rule_checker.py)  <-- No AI, Regex/Text Parsing
                   |
                   v
   AI Diagnoser Engine (src/ai_diagnoser.py)        <-- Mock Offline Mode / Live Anthropic API
                   |
                   v
   Evidence Comparison & Rule Alignment (src/main.py)
                   |
                   v
   Human-in-the-Loop Review (src/human_review.py)   <-- ACCEPT / EDIT / REJECT (Mandatory)
                   |
                   v
   Final Diagnosis & Log Persistence (outputs/review_log.json)
                   |
                   v
   Streamlit Dashboard & Responsible AI Analytics (src/dashboard.py)
```

---

## 7. Dataset Architecture & Schema

The dataset is stored in canonical JSON format ([data/sample_cases.json](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/data/sample_cases.json)) and mirrored in CSV ([data/cases.csv](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/data/cases.csv)).

### Dataset Composition (35 Cases Total)

* **VLAN (5 cases):** `CASE-001`–`CASE-005` (Access VLAN mismatch, trunk pruning, undefined VLAN, access port on trunk, err-disabled port).
* **Gateway (4 cases):** `CASE-007`–`CASE-010` (Gateway IP mismatch, sub-interface admin down, subnet mask mismatch, missing default route).
* **DHCP (5 cases):** `CASE-011`–`CASE-015` (APIPA self-assignment, pool exhaustion, incorrect default-router, missing pool, IP collision).
* **DNS (4 cases):** `CASE-016`–`CASE-019` (Resolver failure, wrong DNS handed by DHCP, DNS server host down, invalid 0.0.0.0 DNS).
* **Routing (5 cases):** `CASE-020`–`CASE-024` (OSPF network unadvertised, missing static route, bad next-hop, asymmetric routing, empty routing table).
* **ACL (4 cases):** `CASE-025`–`CASE-028` (Explicit deny blocking server, VTY SSH access-class deny, missing permit line, NAT source ACL deny).
* **NAT (4 cases):** `CASE-006`, `CASE-029`–`CASE-031` (Stale static NAT after server rebuild, missing `ip nat inside`, 0 active translations, port pool exhaustion).
* **Wireless (4 cases):** `CASE-032`–`CASE-035` (SSID security mismatch, bridge-group mismatch, 2.4GHz co-channel interference, hidden SSID guest-mode disabled).

---

## 8. Deterministic Rule Checker Engine

Module [src/rule_checker.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/src/rule_checker.py) executes 12 deterministic, regex-based checks:

1. `check_duplicate_ip`: Detects identical IPv4 addresses assigned to multiple interfaces or hosts.
2. `check_wrong_subnet_mask`: Identifies host mask disagreements on the same `/24` subnet.
3. `check_gateway_mismatch`: Flags host default gateways that do not correspond to any observed router interface IP.
4. `check_interface_down`: Detects interfaces marked `administratively down`, `down/down`, or `err-disabled`.
5. `check_missing_vlan`: Identifies switchports assigned to VLAN IDs missing from `show vlan brief`.
6. `check_missing_route`: Scans `show ip route` for `-- no entry`, `routing table is empty`, or `not advertised`.
7. `check_trunk_mismatch`: Detects pruned VLANs on 802.1q trunks or links where trunking failed to form.
8. `check_missing_dhcp_pool`: Verifies that router interface subnets have corresponding DHCP pools configured.
9. `check_incorrect_dhcp_network`: Flags DHCP pools whose `default-router` lies outside the pool's network subnet.
10. `check_acl_blocking`: Flags explicit `deny` lines in extended/standard ACLs affecting target subnets.
11. `check_nat_missing`: Verifies that `ip nat inside` and `ip nat outside` interface markings exist when NAT rules are present.
12. `check_nat_translation_absent`: Flags active NAT configurations reporting `Total active translations: 0`.

---

## 9. AI Diagnosis Engine & Evidence Grounding

Module [src/ai_diagnoser.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/src/ai_diagnoser.py) isolates all AI integration behind `diagnose(case, rule_findings)`.

### Structured Output Schema
```json
{
  "root_cause": "Detailed description of expected fault",
  "confidence": 88,
  "osi_layer": "Layer 2 (Data Link)",
  "evidence": ["Exact raw line from show_outputs"],
  "next_command": "show vlan brief",
  "fix_steps": ["Step 1", "Step 2", "Step 3"],
  "severity": "High",
  "concept": "Trunk allowed-VLAN misconfiguration",
  "needs_human_review": true
}
```

### Evidence Grounding Policy
* **100% Raw Line Citation:** For all 30 normal troubleshooting cases, `_pick_evidence_lines()` extracts raw, literal lines directly from the case's `show_outputs` dictionary.
* **Corroborated Confidence Calibration:** When a deterministic rule fires, confidence is calibrated to `88%–96%`; without rule corroboration, confidence defaults to `68%`.
* **Live Mode Fallback:** In `MOCK_MODE=false`, API key errors, network timeouts, or malformed LLM responses are caught and handled gracefully by `_fallback_diagnosis()` returning `confidence: 0` and `needs_human_review: true`.

---

## 10. Mandatory Human Review & Responsible AI Framework

Module [src/human_review.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/src/human_review.py) enforces human oversight.

### Decision Rules
* `ACCEPT`: Human agrees with AI diagnosis.
* `EDIT`: Human modifies the AI root cause; requires a non-empty `corrected_diagnosis` and `reason_for_correction`.
* `REJECT`: Human rejects the AI diagnosis; requires a non-empty `corrected_diagnosis` and `reason_for_correction`.

### Documented Responsible AI Cases (5 Correction Examples)

1. **`CASE-025` (ACL vs Routing):** AI suggested missing route (`64%` confidence) -> Human corrected to explicit `deny` in `SERVER_ACL` line 20.
2. **`CASE-012` (DHCP Pool Exhaustion vs Service Outage):** AI suggested DHCP daemon stopped (`58%` confidence) -> Human corrected to pool exhaustion (30/30 addresses leased).
3. **`CASE-004` (Trunk Not Formed vs Access VLAN Mismatch):** AI suggested VLAN ID mismatch (`61%` confidence) -> Human corrected to access port mode used on inter-switch link.
4. **`CASE-008` (Gateway Interface Admin Down vs DNS Error):** AI suggested DNS server failure (`55%` confidence) -> Human corrected to sub-interface `Gi0/0.20` administratively down.
5. **`CASE-028` (NAT Source ACL Deny vs Missing PAT Config):** AI suggested NAT overload missing (`66%` confidence) -> Human corrected to `NAT_SRC` ACL line 10 explicitly denying source subnet.

---

## 11. Streamlit Dashboard Architecture

The dashboard ([src/dashboard.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/src/dashboard.py)) is organized into 5 tabs:

1. **Overview Tab:** Summary metrics for total cases (35), cases diagnosed (35), Accepted (30), Edited (5), Rejected (0), and AI-Human Agreement Rate (`85.7%`).
2. **Issue Analysis Tab:** Interactive bar chart and tabular breakdown of the 8 canonical issue categories.
3. **Severity Breakdown Tab:** Categorical bar chart showing distribution across Low (4), Medium (10), High (17), and Critical (4) severities.
4. **Responsible AI Tab:** Metrics showing Human Correction Rate (`14.3%`) and an interactive dataframe rendering [responsible_ai_log.csv](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/data/responsible_ai_log.csv).
5. **Case Detail Tab:** Deep inspector view showing symptom, topology note, collapsible `show` command outputs, rule checker findings, AI diagnosis, and persisted human review decisions for any selected case.

---

## 12. Command-Line Interface (CLI) Pipeline

Module [src/main.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/src/main.py) provides a complete CLI interface:

* `python src/main.py --list`: Formats and lists all 35 cases with severity and symptom.
* `python src/main.py --case CASE-025`: Executes interactive 5-step analysis and human review prompt for a target case.
* `python src/main.py --demo`: Runs the guided 10-minute demonstration script (`CASE-025`).
* `python src/main.py --batch`: Executes non-interactive evaluation across all 35 cases and writes results to [outputs/sample_diagnoses.json](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/outputs/sample_diagnoses.json).

---

## 13. Testing, Quality Assurance & Verification Results

### Final Test Suite Summary
* **Test Suite Location:** [tests/test_cases.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/tests/test_cases.py), [tests/test_rule_checker.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/tests/test_rule_checker.py), [tests/test_ai_diagnoser.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/tests/test_ai_diagnoser.py)
* **Total Automated Tests:** 45
* **Tests Passed:** 45
* **Tests Failed:** 0
* **Execution Time:** 0.49 seconds

### Test Verification Matrix
* Dataset Schema & Category Integrity: 9 tests (100% pass)
* Deterministic Rule Checker Checks: 23 tests (100% pass)
* AI Diagnoser & Responsible AI Validation: 12 tests (100% pass)
* CASE-001 Topology Note Consistency: 1 test (100% pass)
* Headless Dashboard Script Runner (`AppTest`): 0 exceptions (100% pass)

---

## 14. Project Limitations

1. **Lab Scope:** The regex rule checker is optimized for Cisco IOS / Packet Tracer CLI syntax rather than multi-vendor NETCONF/YANG schemas.
2. **Offline Mock Calibration:** Mock mode diagnoses simulate LLM responses for demonstration predictability; live mode performance depends on external Anthropic API availability.
3. **No Direct Device Mutation:** By design, NetSage AI does not execute write commands (`config t`, `no shutdown`, `ip route`) on active hardware.

---

## 15. Future Scope & Enhancements

1. **pyATS / Genie Integration:** Replace regex-based rule checking with Cisco pyATS parsed operational state objects.
2. **Multi-Reviewer Role-Based Access Control (RBAC):** Extend `human_review.py` to support authentication and peer review diffing.
3. **Automated Few-Shot Feedback Loop:** Dynamically update `prompts/few_shot_examples.md` using human-edited corrections from `outputs/review_log.json`.

---

## 16. Conclusion

NetSage AI demonstrates that combining deterministic rule parsing with evidence-grounded LLM reasoning creates a highly effective, safe, and transparent network troubleshooting assistant. By enforcing mandatory human review and grounding all evidence citations in raw command outputs, NetSage AI mitigates AI hallucinations while empowering junior network engineers to diagnose complex network anomalies across Layer 1 to Layer 7.

---

## 17. References

1. Cisco Systems, *Cisco IOS Bridging and IBM Networking Command Reference*, Cisco Press.
2. Anthropic API Documentation, *Structured Output and System Prompt Design for Claude*, 2026.
3. Streamlit Documentation, *AppTest Automated Testing Framework for Streamlit Applications*, 2026.
