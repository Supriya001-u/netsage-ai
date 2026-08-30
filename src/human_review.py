"""
human_review.py
------------------
Implements the mandatory human-in-the-loop review step. Every AI diagnosis
must be reviewed and marked ACCEPT / EDIT / REJECT before it is considered
"final". Reviews are appended to outputs/review_log.json (created on first
use) so the dashboard and responsible-AI reporting can read them back.
"""
import os

from utils import OUTPUTS_DIR, load_json, now_iso, save_json

REVIEW_LOG_PATH = os.path.join(OUTPUTS_DIR, "review_log.json")
VALID_DECISIONS = {"ACCEPT", "EDIT", "REJECT"}


def load_reviews():
    if os.path.exists(REVIEW_LOG_PATH):
        return load_json(REVIEW_LOG_PATH)
    return []


def save_review(case_id, ai_diagnosis, reviewer_decision, corrected_diagnosis=None,
                 reviewer_comments=None, reason_for_correction=None, reviewer_name="viva_demo_user"):
    """Record a single human review decision. Raises ValueError on bad input
    so a caller (CLI or dashboard) can surface a clear error instead of
    silently storing garbage."""
    reviewer_decision = reviewer_decision.upper().strip()
    if reviewer_decision not in VALID_DECISIONS:
        raise ValueError(f"reviewer_decision must be one of {VALID_DECISIONS}, got {reviewer_decision!r}")

    if reviewer_decision in ("EDIT", "REJECT") and not corrected_diagnosis:
        raise ValueError(f"{reviewer_decision} requires a corrected_diagnosis")

    entry = {
        "case_id": case_id,
        "reviewer_name": reviewer_name,
        "reviewed_at": now_iso(),
        "ai_diagnosis_full": ai_diagnosis,
        "ai_root_cause": ai_diagnosis.get("root_cause"),
        "ai_confidence": ai_diagnosis.get("confidence"),
        "reviewer_decision": reviewer_decision,
        "corrected_diagnosis": corrected_diagnosis,
        "reviewer_comments": reviewer_comments,
        "reason_for_correction": reason_for_correction,
        "final_diagnosis": corrected_diagnosis if reviewer_decision in ("EDIT", "REJECT")
        else ai_diagnosis.get("root_cause"),
    }

    reviews = load_reviews()
    reviews = [r for r in reviews if r["case_id"] != case_id]  # replace any prior review
    reviews.append(entry)
    save_json(REVIEW_LOG_PATH, reviews)
    return entry


def get_review(case_id):
    for r in load_reviews():
        if r["case_id"] == case_id:
            return r
    return None


def agreement_rate(reviews=None):
    """AI-human agreement rate = ACCEPT count / total reviewed."""
    reviews = reviews if reviews is not None else load_reviews()
    if not reviews:
        return None
    accepted = sum(1 for r in reviews if r["reviewer_decision"] == "ACCEPT")
    return round(100 * accepted / len(reviews), 1)


def review_counts(reviews=None):
    reviews = reviews if reviews is not None else load_reviews()
    counts = {"ACCEPT": 0, "EDIT": 0, "REJECT": 0}
    for r in reviews:
        counts[r["reviewer_decision"]] += 1
    return counts


if __name__ == "__main__":
    # Small smoke test
    fake_ai = {"root_cause": "Test root cause", "confidence": 80}
    save_review("CASE-TEST", fake_ai, "EDIT",
                corrected_diagnosis="Actual root cause",
                reason_for_correction="Evidence line X shows Y")
    print(load_reviews())
    print("Agreement rate:", agreement_rate())
