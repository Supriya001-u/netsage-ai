"""
tests/test_ai_diagnoser.py
------------------------------
Tests for:
  - The mock AI diagnoser's response structure (schema, value ranges,
    mandatory human review, category-driven templates).
  - Responsible AI log data integrity (data/responsible_ai_log.csv).

These run entirely offline in mock mode — no API key or network access
required.

Run with:
    python3 -m pytest tests/ -v
or:
    python3 tests/test_ai_diagnoser.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("MOCK_MODE", "true")  # ensure offline mock mode for these tests

from ai_diagnoser import KNOWN_AI_MISTAKES, MOCK_MODE, REQUIRED_FIELDS, diagnose  # noqa: E402
from case_loader import get_case_by_id, load_cases  # noqa: E402
from rule_checker import run_all_checks  # noqa: E402
from utils import DATA_DIR  # noqa: E402

RESPONSIBLE_AI_LOG_PATH = os.path.join(DATA_DIR, "responsible_ai_log.csv")
REQUIRED_LOG_COLUMNS = [
    "case_id", "ai_diagnosis", "ai_confidence", "correct_diagnosis",
    "reviewer_decision", "correction", "reason", "lesson_learned",
]


def test_mock_mode_is_the_default():
    assert MOCK_MODE is True, "MOCK_MODE must default to true so the app runs with no API key"


def test_diagnose_returns_all_required_fields():
    cases = load_cases()
    case = get_case_by_id("CASE-007", cases)
    result = diagnose(case, run_all_checks(case))
    for field in REQUIRED_FIELDS:
        assert field in result, f"diagnosis missing required field '{field}'"


def test_diagnose_confidence_in_valid_range():
    cases = load_cases()
    for case_id in ["CASE-001", "CASE-011", "CASE-025", "CASE-032"]:
        case = get_case_by_id(case_id, cases)
        result = diagnose(case, run_all_checks(case))
        assert 0 <= result["confidence"] <= 100, \
            f"{case_id}: confidence {result['confidence']} out of range"


def test_diagnose_always_needs_human_review():
    cases = load_cases()
    for case in cases[:10]:
        result = diagnose(case, run_all_checks(case))
        assert result["needs_human_review"] is True, \
            f"{case['case_id']}: needs_human_review must always be True"


def test_diagnose_evidence_and_fix_steps_are_nonempty_lists():
    cases = load_cases()
    case = get_case_by_id("CASE-025", cases)
    result = diagnose(case, run_all_checks(case))
    assert isinstance(result["evidence"], list) and len(result["evidence"]) >= 1
    assert isinstance(result["fix_steps"], list) and len(result["fix_steps"]) >= 1


def test_diagnose_over_full_dataset_never_crashes():
    """Every case in the dataset must produce a valid mock diagnosis without
    raising — a real smoke test of the whole dataset x diagnoser pairing."""
    cases = load_cases()
    for case in cases:
        result = diagnose(case, run_all_checks(case))
        for field in REQUIRED_FIELDS:
            assert field in result, f"{case['case_id']} missing '{field}'"


def test_known_mistake_cases_produce_the_documented_wrong_diagnosis():
    """The 5 cases used for the Responsible AI log must reproducibly return
    their documented (deliberately wrong) mock diagnosis."""
    cases = load_cases()
    for case_id, mistake in KNOWN_AI_MISTAKES.items():
        case = get_case_by_id(case_id, cases)
        assert case is not None, f"{case_id} referenced in KNOWN_AI_MISTAKES but not in dataset"
        result = diagnose(case, run_all_checks(case))
        assert result["root_cause"] == mistake["root_cause"]
        assert result["confidence"] == mistake["confidence"]


def test_responsible_ai_log_file_exists_and_has_required_columns():
    assert os.path.exists(RESPONSIBLE_AI_LOG_PATH), "data/responsible_ai_log.csv is missing"
    with open(RESPONSIBLE_AI_LOG_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        for col in REQUIRED_LOG_COLUMNS:
            assert col in reader.fieldnames, f"responsible_ai_log.csv missing column '{col}'"
    assert len(rows) >= 5, f"Responsible AI log must have at least 5 rows, found {len(rows)}"


def test_responsible_ai_log_rows_reference_real_cases():
    cases = load_cases()
    case_ids = {c["case_id"] for c in cases}
    with open(RESPONSIBLE_AI_LOG_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        assert row["case_id"] in case_ids, \
            f"responsible_ai_log.csv references unknown case_id {row['case_id']}"
        assert row["ai_diagnosis"].strip(), f"{row['case_id']}: empty ai_diagnosis"
        assert row["correct_diagnosis"].strip(), f"{row['case_id']}: empty correct_diagnosis"
        assert row["reviewer_decision"].strip().upper() in ("ACCEPT", "EDIT", "REJECT")
        assert row["reason"].strip(), f"{row['case_id']}: empty reason"
        assert row["lesson_learned"].strip(), f"{row['case_id']}: empty lesson_learned"


def test_responsible_ai_log_confidence_matches_known_mistakes():
    """The logged ai_confidence values must match what the running mock
    diagnoser actually produces for those cases (log is not just prose)."""
    with open(RESPONSIBLE_AI_LOG_PATH, newline="", encoding="utf-8") as f:
        rows = {row["case_id"]: row for row in csv.DictReader(f)}
    for case_id, mistake in KNOWN_AI_MISTAKES.items():
        assert case_id in rows, f"{case_id} missing from responsible_ai_log.csv"
        assert int(rows[case_id]["ai_confidence"]) == mistake["confidence"]


def test_normal_mock_ai_evidence_exists_in_raw_show_outputs():
    """Every normal (non-mistake) case's mock AI diagnosis evidence lines must
    literally exist inside its raw show_command output."""
    from utils import flatten_show_outputs
    cases = load_cases()
    for case in cases:
        if case["case_id"] in KNOWN_AI_MISTAKES:
            continue
        result = diagnose(case, run_all_checks(case))
        raw_text = flatten_show_outputs(case["show_outputs"])
        for item in result["evidence"]:
            assert item in raw_text, (
                f"{case['case_id']}: Evidence citation '{item}' not found in raw show_outputs text"
            )


def test_known_ai_mistakes_exempt_from_raw_evidence_grounding():
    """The 5 KNOWN_AI_MISTAKES cases are exempt from exact raw evidence matching
    because they intentionally simulate incorrect AI reasoning / hallucinations."""
    cases = load_cases()
    assert len(KNOWN_AI_MISTAKES) == 5
    for case_id, mistake in KNOWN_AI_MISTAKES.items():
        case = get_case_by_id(case_id, cases)
        result = diagnose(case, run_all_checks(case))
        assert result["root_cause"] == mistake["root_cause"]



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
