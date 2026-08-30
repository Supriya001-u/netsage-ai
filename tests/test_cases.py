"""
tests/test_cases.py
----------------------
Validates the dataset itself: every case has the required fields, the
category-coverage requirement from the brief is met (>= 30 cases covering
VLAN/gateway/DHCP/DNS/routing/ACL/NAT/wireless), and every case's evidence
is internally non-empty.

Run with:
    python3 -m pytest tests/ -v
or:
    python3 tests/test_cases.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from case_loader import CANONICAL_CATEGORIES, dataset_summary, filter_cases, get_case_by_id, load_cases  # noqa: E402

REQUIRED_FIELDS = [
    "case_id", "symptom", "topology_note", "show_outputs",
    "expected_fault", "osi_layer", "concept", "severity", "category",
]
REQUIRED_CATEGORIES = CANONICAL_CATEGORIES
VALID_SEVERITIES = {"Low", "Medium", "High", "Critical"}
# Approximate target distribution from the project audit; used as a sanity
# range rather than an exact equality check so minor future edits don't
# break the test suite.
TARGET_DISTRIBUTION = {
    "vlan": 5, "gateway": 4, "dhcp": 5, "dns": 4,
    "routing": 5, "acl": 4, "nat": 4, "wireless": 4,
}


def test_at_least_thirty_cases():
    cases = load_cases()
    assert len(cases) >= 30, f"Expected at least 30 cases, found {len(cases)}"


def test_every_case_has_required_fields():
    cases = load_cases()
    for c in cases:
        for field in REQUIRED_FIELDS:
            assert field in c and c[field], f"{c.get('case_id', '?')} missing field '{field}'"


def test_every_case_has_at_least_one_show_output():
    cases = load_cases()
    for c in cases:
        assert isinstance(c["show_outputs"], dict) and len(c["show_outputs"]) >= 1, \
            f"{c['case_id']} has no show_outputs evidence"


def test_case_ids_are_unique():
    cases = load_cases()
    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids)), "Duplicate case_id values found in dataset"


def test_severity_values_are_valid():
    cases = load_cases()
    for c in cases:
        assert c["severity"] in VALID_SEVERITIES, \
            f"{c['case_id']} has invalid severity '{c['severity']}'"


def test_all_required_categories_covered():
    cases = load_cases()
    for category in REQUIRED_CATEGORIES:
        matches = filter_cases(cases, category=category)
        assert len(matches) >= 1, f"No cases found covering category '{category}'"


def test_every_case_has_a_valid_canonical_category():
    cases = load_cases()
    for c in cases:
        assert c.get("category") in CANONICAL_CATEGORIES, \
            f"{c['case_id']} has invalid/missing category '{c.get('category')}'"


def test_category_distribution_matches_target_and_sums_to_total():
    """Regression test for the fuzzy-keyword miscounting bug found during
    audit: category counts must be exact (no double-counting) and close to
    the agreed target distribution."""
    cases = load_cases()
    summary = dataset_summary(cases)
    assert sum(summary["by_category"].values()) == summary["total_cases"], \
        "by_category counts must sum to exactly total_cases (no overlap/double-count)"
    for category, target in TARGET_DISTRIBUTION.items():
        actual = summary["by_category"][category]
        assert abs(actual - target) <= 1, \
            f"Category '{category}': expected ~{target} cases, found {actual}"


def test_case_001_topology_note_no_longer_contradicts_evidence():
    """CASE-001's topology note must describe intended VLAN configuration rather
    than asserting both Fa0/1 and Fa0/2 were configured for VLAN 10."""
    cases = load_cases()
    case1 = get_case_by_id("CASE-001", cases)
    assert "configured as access ports for vlan 10" not in case1["topology_note"].lower(), \
        "CASE-001 topology_note contains stale contradiction"
    assert "intended to be access ports for vlan 10" in case1["topology_note"].lower()



def _run_all_tests_manually():
    test_fns = [obj for name, obj in globals().items()
                if name.startswith("test_") and callable(obj)]
    passed, failed = 0, 0
    for fn in test_fns:
        try:
            fn()
            print(f"PASS: {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {fn.__name__} -> {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    _run_all_tests_manually()
