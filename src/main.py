"""
main.py
--------
Command-line entry point for NetSage AI. Implements the full pipeline
from the brief:

    INPUT -> case selection -> rule-based validation -> AI diagnosis ->
    evidence comparison -> human review -> Accepted/Edited/Rejected ->
    final diagnosis -> dashboard/logging

Usage:
    python3 main.py --list
    python3 main.py --case CASE-025
    python3 main.py --demo
    python3 main.py --batch          (run every case in mock mode, no prompts)
"""
import argparse
import json
import sys

from ai_diagnoser import MOCK_MODE, diagnose
from case_loader import get_case_by_id, load_cases
from human_review import save_review
from rule_checker import run_all_checks
from utils import OUTPUTS_DIR, flatten_show_outputs, save_json, truncate

DEMO_CASE_ID = "CASE-025"  # the "especially good" demo case (ACL blocking a server subnet)


def print_header(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def show_case(case):
    print_header(f"{case['case_id']} — {case['severity']} severity")
    print(f"Symptom:\n  {case['symptom']}\n")
    print(f"Topology note:\n  {case['topology_note']}\n")
    print("Evidence (show command output):")
    print(flatten_show_outputs(case["show_outputs"]))


def show_rule_findings(findings):
    print_header("STEP 1: Deterministic rule checker (no AI)")
    fired = [f for f in findings if f["status"] != "PASS"]
    if not fired:
        print("No deterministic rule fired for this case — this is a case where "
              "structural config parsing alone is not enough; AI evidence "
              "reasoning is needed.")
    for f in fired:
        print(f"[{f['status']}] {f['check']} (severity: {f['severity']})")
        print(f"  Evidence: {f['evidence']}")
        print(f"  {f['message']}\n")


def show_ai_diagnosis(diagnosis):
    print_header(f"STEP 2: AI diagnosis ({'MOCK' if MOCK_MODE else 'LIVE LLM'} mode)")
    print(f"Root cause : {diagnosis['root_cause']}")
    print(f"Confidence : {diagnosis['confidence']}%")
    print(f"OSI layer  : {diagnosis['osi_layer']}")
    print("Evidence cited:")
    for e in diagnosis["evidence"]:
        print(f"  - {truncate(e)}")
    print(f"Next command   : {diagnosis['next_command']}")
    print("Recommended fix steps (NOT auto-applied):")
    for step in diagnosis["fix_steps"]:
        print(f"  - {step}")
    print(f"Needs human review: {diagnosis['needs_human_review']}")


def compare_evidence(case, diagnosis):
    print_header("STEP 3: Evidence comparison vs. known correct answer")
    match = diagnosis["root_cause"].strip().lower() == case["expected_fault"].strip().lower()
    print(f"Dataset's expected_fault : {case['expected_fault']}")
    print(f"AI's root_cause          : {diagnosis['root_cause']}")
    print(f"Exact match with dataset : {match}")
    if not match:
        print("-> This is exactly the kind of gap the human reviewer must catch.")
    return match


def prompt_human_review(case, diagnosis, interactive=True):
    print_header("STEP 4: Human review (Accept / Edit / Reject)")
    if not interactive:
        # Non-interactive batch mode: auto-decide using the dataset's known
        # answer purely so batch runs produce a usable log; a real user
        # would do this manually in --demo / --case mode.
        if diagnosis["root_cause"].strip().lower() == case["expected_fault"].strip().lower():
            decision, corrected, reason = "ACCEPT", None, None
        else:
            decision = "EDIT"
            corrected = case["expected_fault"]
            reason = "Corrected against known evidence during batch validation run."
        entry = save_review(case["case_id"], diagnosis, decision, corrected, None, reason)
        print(f"[batch mode] recorded decision: {decision}")
        return entry

    print("Options: [A]ccept  [E]dit  [R]eject")
    decision = None
    for attempt in range(3):
        try:
            choice = input("Your decision: ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nNo input received — aborting this review without saving a decision.")
            return None
        candidate = {"A": "ACCEPT", "E": "EDIT", "R": "REJECT"}.get(choice, choice)
        if candidate in ("ACCEPT", "EDIT", "REJECT"):
            decision = candidate
            break
        print(f"'{choice}' is not a valid option. Please enter A, E, or R.")
    if decision is None:
        print("Too many invalid entries — aborting this review without saving a decision.")
        return None

    corrected, reason, comments = None, None, None
    if decision in ("EDIT", "REJECT"):
        while not corrected:
            try:
                corrected = input("Corrected diagnosis (required): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nNo input received — aborting this review without saving a decision.")
                return None
            if not corrected:
                print("A corrected diagnosis is required for EDIT/REJECT — please try again.")
        try:
            reason = input("Reason for correction (cite the evidence line): ").strip()
        except (EOFError, KeyboardInterrupt):
            reason = ""
    try:
        comments = input("Any additional reviewer comments (optional): ").strip() or None
    except (EOFError, KeyboardInterrupt):
        comments = None

    entry = save_review(case["case_id"], diagnosis, decision, corrected, comments, reason)
    return entry


def show_final(case, review_entry):
    print_header("STEP 5: Final diagnosis")
    if review_entry is None:
        print("No review decision was recorded for this case (input was aborted).")
        print("Re-run this command to complete the human review step.")
        return
    print(f"Reviewer decision : {review_entry['reviewer_decision']}")
    print(f"Final diagnosis   : {review_entry['final_diagnosis']}")
    print("\nThis result is now logged to outputs/review_log.json for the "
          "dashboard's Accepted/Edited/Rejected and AI-human agreement metrics.")


def run_pipeline(case, interactive=True):
    findings = run_all_checks(case)
    show_case(case)
    show_rule_findings(findings)
    diagnosis = diagnose(case, findings)
    show_ai_diagnosis(diagnosis)
    compare_evidence(case, diagnosis)
    review_entry = prompt_human_review(case, diagnosis, interactive=interactive)
    show_final(case, review_entry)
    return {"case": case, "findings": findings, "diagnosis": diagnosis, "review": review_entry}


def run_batch(cases):
    results = []
    for case in cases:
        findings = run_all_checks(case)
        diagnosis = diagnose(case, findings)
        review_entry = prompt_human_review(case, diagnosis, interactive=False)
        results.append({
            "case_id": case["case_id"],
            "diagnosis": diagnosis,
            "review": review_entry,
        })
        print(f"{case['case_id']}: AI confidence={diagnosis['confidence']}% "
              f"-> reviewer={review_entry['reviewer_decision']}")
    save_json(f"{OUTPUTS_DIR}/sample_diagnoses.json", results)
    print(f"\nSaved {len(results)} diagnoses to outputs/sample_diagnoses.json")
    return results


def main():
    parser = argparse.ArgumentParser(description="NetSage AI troubleshooting pipeline")
    parser.add_argument("--list", action="store_true", help="List all available cases")
    parser.add_argument("--case", type=str, help="Run the pipeline for a specific case_id")
    parser.add_argument("--demo", action="store_true",
                         help=f"Run the guided demo case ({DEMO_CASE_ID})")
    parser.add_argument("--batch", action="store_true",
                         help="Run all cases non-interactively (mock mode) and save outputs")
    args = parser.parse_args()

    cases = load_cases()

    if args.list:
        for c in cases:
            print(f"{c['case_id']:10} [{c['severity']:8}] {c['symptom'][:70]}")
        return

    if args.batch:
        run_batch(cases)
        return

    case_id = args.case or (DEMO_CASE_ID if args.demo else None)
    if not case_id:
        parser.print_help()
        return

    case = get_case_by_id(case_id, cases)
    if not case:
        print(f"No such case: {case_id}", file=sys.stderr)
        sys.exit(1)

    run_pipeline(case, interactive=True)


if __name__ == "__main__":
    main()
