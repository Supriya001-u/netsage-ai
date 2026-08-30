# Human Reviewer Prompt / Guidance

This is not an LLM prompt — it is the on-screen guidance shown to the human
reviewer in `src/human_review.py` and the Streamlit dashboard, so reviewers
apply a consistent standard when deciding ACCEPT / EDIT / REJECT.

---

## Before you decide

1. Re-read the symptom and topology note yourself — do not only read the
   AI's summary of them.
2. Open the raw `show_outputs` evidence and confirm the AI's cited
   evidence lines actually say what the AI claims they say.
3. Check the deterministic rule-checker findings for this case. If the
   rule checker flagged something the AI did **not** mention, treat that
   as a red flag.
4. Consider the AI's stated confidence. Low confidence is not itself a
   reason to reject — it may be an honest admission that more evidence is
   needed, which you can supply next.

## Decision options

- **ACCEPT** — the root cause, evidence citation, and fix steps are all
  correct and evidence-backed. You are willing to sign off on running the
  suggested next command / fix in a real (or lab) environment.

- **EDIT** — the AI was on the right track (or partially right) but the
  root cause, evidence, or fix steps need a correction before they should
  be acted on. You must supply:
  - `corrected_diagnosis` — the corrected root cause in your own words.
  - `reason` — which evidence line proves the AI's version wrong or
    incomplete.

- **REJECT** — the AI's diagnosis is unsupported by the evidence, or is
  actively contradicted by it. You must supply:
  - `corrected_diagnosis` — what you believe the actual root cause is (or
    "insufficient evidence" if you genuinely cannot tell yet).
  - `reason` — why the AI's version does not hold up.

## Required fields for every review

| Field                | Required | Notes                                             |
|-----------------------|----------|----------------------------------------------------|
| reviewer_decision      | Yes      | one of ACCEPT / EDIT / REJECT                     |
| corrected_diagnosis    | EDIT/REJECT only | the reviewer's corrected root cause      |
| reviewer_comments      | Optional | free-text notes for the record                    |
| reason_for_correction  | EDIT/REJECT only | which evidence line drove the correction |

## A reminder on responsible AI

NetSage AI is a **decision-support** tool, not an autonomous agent. No fix
is ever applied automatically. Every single case — regardless of AI
confidence — passes through this review step before any recommended
command or config change would be considered for use in a real network.
