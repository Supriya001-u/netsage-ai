"""
case_loader.py
---------------
Loads troubleshooting cases from data/sample_cases.json (or data/cases.csv
as a fallback) and provides simple lookup/filter helpers used by main.py
and dashboard.py.
"""
import csv
import json
import os

from utils import DATA_DIR


def load_cases():
    """Load all cases as a list of dicts. Prefers the JSON file (nested
    show_outputs), falls back to the CSV (show_outputs stored as a JSON
    string in a single column)."""
    json_path = os.path.join(DATA_DIR, "sample_cases.json")
    csv_path = os.path.join(DATA_DIR, "cases.csv")

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if os.path.exists(csv_path):
        cases = []
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["show_outputs"] = json.loads(row["show_outputs"])
                cases.append(row)
        return cases

    raise FileNotFoundError(
        "No dataset found. Expected data/sample_cases.json or data/cases.csv."
    )


CANONICAL_CATEGORIES = ["vlan", "gateway", "dhcp", "dns", "routing", "acl", "nat", "wireless"]


def get_case_by_id(case_id, cases=None):
    cases = cases or load_cases()
    for c in cases:
        if c["case_id"] == case_id:
            return c
    return None


def filter_cases(cases=None, category=None, severity=None):
    """Filter by the case's canonical 'category' field (exact match,
    case-insensitive) and/or exact severity.

    NOTE: earlier versions of this function matched a category keyword as a
    loose substring against the symptom/concept/expected_fault text. That
    approach double-counted cases whose *symptom description* happened to
    mention another category's keyword (e.g. a gateway case whose symptom
    text says "VLAN 20 lost access..." was being counted as a VLAN case
    too), which fed fabricated-looking statistics into the dashboard. Every
    case now carries an explicit, single-valued 'category' field assigned
    at dataset-generation time (see tools_generate_data.py), and this
    function matches against that field directly.
    """
    cases = cases or load_cases()
    result = cases
    if category:
        category = category.lower()
        result = [c for c in result if c.get("category", "").lower() == category]
    if severity:
        result = [c for c in result if c["severity"].lower() == severity.lower()]
    return result


def dataset_summary(cases=None):
    """Counts used by the dashboard / self-audit checklist. Uses the exact,
    non-overlapping 'category' field, so by_category values always sum to
    total_cases."""
    cases = cases or load_cases()
    by_category = {cat: 0 for cat in CANONICAL_CATEGORIES}
    for c in cases:
        cat = c.get("category", "").lower()
        if cat in by_category:
            by_category[cat] += 1

    by_severity = {}
    for c in cases:
        by_severity[c["severity"]] = by_severity.get(c["severity"], 0) + 1

    assert sum(by_category.values()) == len(cases), (
        "by_category counts do not sum to total_cases — every case must "
        "have a valid 'category' field from CANONICAL_CATEGORIES."
    )

    return {
        "total_cases": len(cases),
        "by_category": by_category,
        "by_severity": by_severity,
    }


if __name__ == "__main__":
    cases = load_cases()
    print(f"Loaded {len(cases)} cases")
    print(dataset_summary(cases))
