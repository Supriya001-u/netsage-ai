# NetSage AI — Testing & Validation Strategy

This document details the automated testing suite, validation procedures, quality assurance checks, and execution verification logs for **NetSage AI**.

---

## 1. Testing Overview & Strategy

NetSage AI employs a multi-tiered testing strategy:

1. **Dataset Integrity Testing ([tests/test_cases.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/tests/test_cases.py)):** Verifies case counts, required fields, unique IDs, valid severities, canonical categories, non-overlapping category distribution, and topology note consistency.
2. **Rule Checker Logic Testing ([tests/test_rule_checker.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/tests/test_rule_checker.py)):** Validates positive and negative test cases for all 12 deterministic rule functions.
3. **AI Diagnoser & Responsible AI Testing ([tests/test_ai_diagnoser.py](file:///c:/Users/supri/OneDrive/Desktop/netsage-ai/tests/test_ai_diagnoser.py)):** Validates offline mock mode default settings, schema completeness, confidence calibration range, mandatory human review flags, Responsible AI CSV structure, exact raw evidence line grounding for normal cases, and deliberate mistake exemptions for Responsible AI cases.
4. **Streamlit UI Programmatic Script Runner (`AppTest`):** Programmatically verifies that `src/dashboard.py` executes without uncaught exceptions or rendering errors.

---

## 2. Automated Test Suite Breakdown (45 Tests Total)

### 2.1 File: `tests/test_cases.py` (10 Tests)

| Test Name | Description | Status |
|---|---|---|
| `test_at_least_thirty_cases` | Verifies dataset has $\ge 30$ cases (35 found). | **PASS** |
| `test_every_case_has_required_fields` | Verifies presence of all 9 required schema fields. | **PASS** |
| `test_every_case_has_at_least_one_show_output` | Verifies non-empty `show_outputs` dictionary. | **PASS** |
| `test_case_ids_are_unique` | Asserts zero duplicate `case_id` values exist. | **PASS** |
| `test_severity_values_are_valid` | Verifies severities in `{"Low", "Medium", "High", "Critical"}`. | **PASS** |
| `test_all_required_categories_covered` | Asserts all 8 canonical categories are represented. | **PASS** |
| `test_every_case_has_a_valid_canonical_category` | Asserts category in `CANONICAL_CATEGORIES`. | **PASS** |
| `test_category_distribution_matches_target_and_sums_to_total` | Verifies non-overlapping category counts sum to exactly 35. | **PASS** |
| `test_case_001_topology_note_no_longer_contradicts_evidence` | Verifies `CASE-001` topology note describes intended VLAN configuration without asserting Fa0/2 was configured for VLAN 10. | **PASS** |

---

### 2.2 File: `tests/test_rule_checker.py` (23 Tests)

| Test Name | Target Rule | Scenario Tested | Status |
|---|---|---|---|
| `test_wrong_subnet_mask_detected` | `check_wrong_subnet_mask` | Subnet mask mismatch detected | **PASS** |
| `test_wrong_subnet_mask_pass_when_consistent` | `check_wrong_subnet_mask` | Consistent masks pass cleanly | **PASS** |
| `test_missing_route_detected` | `check_missing_route` | Unadvertised route flagged | **PASS** |
| `test_missing_route_pass_when_populated` | `check_missing_route` | Populated routing table passes | **PASS** |
| `test_trunk_mismatch_vlan_pruned` | `check_trunk_mismatch` | Pruned VLAN on trunk flagged | **PASS** |
| `test_trunk_mismatch_pass_when_all_vlans_allowed` | `check_trunk_mismatch` | Complete allowed list passes | **PASS** |
| `test_trunk_not_formed_detected` | `check_trunk_not_formed` | Access port on inter-switch link flagged | **PASS** |
| `test_acl_blocking_explicit_deny_detected` | `check_acl_blocking` | Explicit deny flagged | **PASS** |
| `test_acl_blocking_pass_when_permit_any_present` | `check_acl_blocking` | Trailing permit passes | **PASS** |
| `test_acl_blocking_standard_acl_no_false_positive` | `check_acl_blocking` | Standard ACL permit-only passes | **PASS** |
| `test_duplicate_ip_detected` | `check_duplicate_ip` | Re-assigned IP detected | **PASS** |
| `test_duplicate_ip_not_falsely_flagged` | `check_duplicate_ip` | Unique IPs pass | **PASS** |
| `test_gateway_mismatch_detected` | `check_gateway_mismatch` | Unreachable gateway IP flagged | **PASS** |
| `test_gateway_mismatch_pass_when_matching` | `check_gateway_mismatch` | Matching router interface passes | **PASS** |
| `test_interface_administratively_down` | `check_interface_down` | Admin down interface flagged | **PASS** |
| `test_interface_up_does_not_false_positive` | `check_interface_down` | Up/up interface passes | **PASS** |
| `test_missing_vlan_detected` | `check_missing_vlan` | Undefined VLAN flagged | **PASS** |
| `test_missing_vlan_pass_when_present` | `check_missing_vlan` | Defined VLAN passes | **PASS** |
| `test_missing_dhcp_pool_detected` | `check_missing_dhcp_pool` | Subnet lacking DHCP pool flagged | **PASS** |
| `test_incorrect_dhcp_network_detected` | `check_incorrect_dhcp_network` | Default-router outside network flagged | **PASS** |
| `test_incorrect_dhcp_network_pass_when_correct` | `check_incorrect_dhcp_network` | Valid default-router passes | **PASS** |
| `test_nat_missing_interface_marking` | `check_nat_missing` | Missing `ip nat inside` flagged | **PASS** |
| `test_nat_translation_absent_detected` | `check_nat_translation_absent` | 0 active translations flagged | **PASS** |
| `test_nat_translation_present_passes` | `check_nat_translation_absent` | Active translations pass | **PASS** |

---

### 2.3 File: `tests/test_ai_diagnoser.py` (12 Tests)

| Test Name | Description | Status |
|---|---|---|
| `test_mock_mode_is_the_default` | Verifies `MOCK_MODE` defaults to `True`. | **PASS** |
| `test_diagnose_returns_all_required_fields` | Verifies diagnosis returns all required keys. | **PASS** |
| `test_diagnose_confidence_in_valid_range` | Asserts confidence $\in [0, 100]$. | **PASS** |
| `test_diagnose_always_needs_human_review` | Asserts `needs_human_review` is unconditionally `True`. | **PASS** |
| `test_diagnose_evidence_and_fix_steps_are_nonempty_lists` | Asserts non-empty lists for evidence and fix steps. | **PASS** |
| `test_diagnose_over_full_dataset_never_crashes` | Evaluates all 35 cases without raising errors. | **PASS** |
| `test_known_mistake_cases_produce_the_documented_wrong_diagnosis` | Verifies 5 Responsible AI cases return deliberate wrong diagnoses. | **PASS** |
| `test_responsible_ai_log_file_exists_and_has_required_columns` | Verifies `responsible_ai_log.csv` columns. | **PASS** |
| `test_responsible_ai_log_rows_reference_real_cases` | Validates log references against case dataset. | **PASS** |
| `test_responsible_ai_log_confidence_matches_known_mistakes` | Verifies confidence calibration match. | **PASS** |
| `test_normal_mock_ai_evidence_exists_in_raw_show_outputs` | **New Test:** Verifies 100% raw line citation grounding across all 30 normal cases. | **PASS** |
| `test_known_ai_mistakes_exempt_from_raw_evidence_grounding` | **New Test:** Verifies 5 Responsible AI mistake cases are explicitly exempt from raw line matching. | **PASS** |

---

## 3. Headless Streamlit Dashboard Verification (`AppTest`)

The dashboard layout and reactive state were programmatically verified using Streamlit's official headless test runner (`AppTest`):

```python
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("src/dashboard.py", default_timeout=10).run()
assert len(at.exception) == 0
```

* **Execution Status:** Success (HTTP 200 OK).
* **Uncaught Exceptions:** 0.

---

## 4. Final Pytest Verification Output Log

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\supri\OneDrive\Desktop\netsage-ai\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\supri\OneDrive\Desktop\netsage-ai
plugins: anyio-4.14.2
collected 45 items

tests/test_ai_diagnoser.py::test_mock_mode_is_the_default PASSED         [  2%]
tests/test_ai_diagnoser.py::test_diagnose_returns_all_required_fields PASSED [  4%]
tests/test_ai_diagnoser.py::test_diagnose_confidence_in_valid_range PASSED [  6%]
tests/test_ai_diagnoser.py::test_diagnose_always_needs_human_review PASSED [  8%]
tests/test_ai_diagnoser.py::test_diagnose_evidence_and_fix_steps_are_nonempty_lists PASSED [ 11%]
tests/test_ai_diagnoser.py::test_diagnose_over_full_dataset_never_crashes PASSED [ 13%]
tests/test_ai_diagnoser.py::test_known_mistake_cases_produce_the_documented_wrong_diagnosis PASSED [ 15%]
tests/test_ai_diagnoser.py::test_responsible_ai_log_file_exists_and_has_required_columns PASSED [ 17%]
tests/test_ai_diagnoser.py::test_responsible_ai_log_rows_reference_real_cases PASSED [ 20%]
tests/test_ai_diagnoser.py::test_responsible_ai_log_confidence_matches_known_mistakes PASSED [ 22%]
tests/test_ai_diagnoser.py::test_normal_mock_ai_evidence_exists_in_raw_show_outputs PASSED [ 24%]
tests/test_ai_diagnoser.py::test_known_ai_mistakes_exempt_from_raw_evidence_grounding PASSED [ 26%]
tests/test_cases.py::test_at_least_thirty_cases PASSED                   [ 28%]
tests/test_cases.py::test_every_case_has_required_fields PASSED          [ 31%]
tests/test_cases.py::test_every_case_has_at_least_one_show_output PASSED [ 33%]
tests/test_cases.py::test_case_ids_are_unique PASSED                     [ 35%]
tests/test_cases.py::test_severity_values_are_valid PASSED               [ 37%]
tests/test_cases.py::test_all_required_categories_covered PASSED         [ 40%]
tests/test_cases.py::test_every_case_has_a_valid_canonical_category PASSED [ 42%]
tests/test_cases.py::test_category_distribution_matches_target_and_sums_to_total PASSED [ 44%]
tests/test_cases.py::test_case_001_topology_note_no_longer_contradicts_evidence PASSED [ 46%]
tests/test_rule_checker.py::test_wrong_subnet_mask_detected PASSED       [ 48%]
tests/test_rule_checker.py::test_wrong_subnet_mask_pass_when_consistent PASSED [ 51%]
tests/test_rule_checker.py::test_missing_route_detected PASSED           [ 53%]
tests/test_rule_checker.py::test_missing_route_pass_when_populated PASSED [ 55%]
tests/test_rule_checker.py::test_trunk_mismatch_vlan_pruned PASSED       [ 57%]
tests/test_rule_checker.py::test_trunk_mismatch_pass_when_all_vlans_allowed PASSED [ 60%]
tests/test_rule_checker.py::test_trunk_not_formed_detected PASSED        [ 62%]
tests/test_rule_checker.py::test_acl_blocking_explicit_deny_detected PASSED [ 64%]
tests/test_rule_checker.py::test_acl_blocking_pass_when_permit_any_present PASSED [ 66%]
tests/test_rule_checker.py::test_acl_blocking_standard_acl_no_false_positive PASSED [ 68%]
tests/test_rule_checker.py::test_duplicate_ip_detected PASSED            [ 71%]
tests/test_rule_checker.py::test_duplicate_ip_not_falsely_flagged PASSED [ 73%]
tests/test_rule_checker.py::test_gateway_mismatch_detected PASSED        [ 75%]
tests/test_rule_checker.py::test_gateway_mismatch_pass_when_matching PASSED [ 77%]
tests/test_rule_checker.py::test_interface_administratively_down PASSED  [ 80%]
tests/test_rule_checker.py::test_interface_up_does_not_false_positive PASSED [ 82%]
tests/test_rule_checker.py::test_missing_vlan_detected PASSED            [ 84%]
tests/test_rule_checker.py::test_missing_vlan_pass_when_present PASSED   [ 86%]
tests/test_rule_checker.py::test_missing_dhcp_pool_detected PASSED       [ 88%]
tests/test_rule_checker.py::test_incorrect_dhcp_network_detected PASSED  [ 91%]
tests/test_rule_checker.py::test_incorrect_dhcp_network_pass_when_correct PASSED [ 93%]
tests/test_rule_checker.py::test_nat_missing_interface_marking PASSED    [ 95%]
tests/test_rule_checker.py::test_nat_translation_absent_detected PASSED  [ 97%]
tests/test_rule_checker.py::test_nat_translation_present_passes PASSED   [100%]

============================= 45 passed in 0.49s ==============================
```
