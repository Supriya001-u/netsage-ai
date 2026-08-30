# Responsible AI in NetSage AI

## Principles this project follows

1. **The AI never acts autonomously.** `ai_diagnoser.diagnose()` sets
   `needs_human_review = True` on every single response, and no other
   module in this codebase applies a configuration change to a device.
   `fix_steps` are always phrased as recommendations for a human to review,
   carry out, and verify.

2. **Every diagnosis is grounded in evidence the system was actually given.**
   The AI prompt (`prompts/diagnose_prompt.md`) explicitly forbids
   inventing evidence, IP addresses, or command output not supplied in the
   case. It must cite the specific evidence line(s) behind its conclusion.

3. **Confidence is calibrated, not inflated.** The prompt gives explicit
   guidance on what different confidence bands mean (see the "Confidence
   calibration guidance" section of the prompt file) and instructs the
   model to lower its confidence and ask for more evidence when the case
   is genuinely ambiguous.

4. **A deterministic, non-AI safety net runs first.** `rule_checker.py`
   performs 12 reproducible checks with plain regex/text parsing before
   the AI is ever consulted, so at least some findings are never subject
   to AI hallucination at all.

5. **Human review is mandatory, not optional, and is tracked.** Every case
   run through `main.py` or the dashboard is logged with a reviewer
   decision (ACCEPT / EDIT / REJECT), a corrected diagnosis where
   applicable, and a reason. `human_review.save_review()` raises an error
   if an EDIT or REJECT is submitted without a correction — a reviewer
   cannot silently wave through a change they disagree with.

## Where the AI gets it wrong (and why that's demonstrated on purpose)

`data/responsible_ai_log.csv` documents 5 cases where NetSage AI's initial
diagnosis was incomplete or incorrect, and a human reviewer corrected it.
Each row includes `case_id`, `ai_diagnosis`, `ai_confidence`,
`correct_diagnosis`, `reviewer_decision`, `correction`, `reason`, and
`lesson_learned`:

| Case | AI's mistake | What the evidence actually showed |
|------|---------------|-------------------------------------|
| CASE-025 | Leaned toward a generic routing explanation | An explicit ACL `deny` line for the exact reporting subnet |
| CASE-012 | Assumed a DHCP *service failure* | The pool was simply exhausted (30/30 leased) |
| CASE-004 | Assumed a simple VLAN-ID *mismatch* | The inter-switch link was never trunked at all |
| CASE-008 | Assumed a DNS misconfiguration | The VLAN's gateway sub-interface was administratively down |
| CASE-028 | Assumed NAT wasn't configured at all | NAT was configured correctly, but its scoping ACL blocked the source subnet |

These are intentionally believable mistakes — each one is a plausible
first read of the symptom that falls apart once the specific evidence line
is checked carefully, which is exactly the situation human review exists
to catch. `src/ai_diagnoser.py`'s `KNOWN_AI_MISTAKES` dictionary reproduces
these same wrong diagnoses live when you run `python3 src/main.py --case
CASE-025` (etc.) in mock mode, so the log is not just a static document —
it matches what the running system actually produces.

## How AI-human agreement is calculated

```
agreement_rate = (number of ACCEPT decisions) / (total reviewed cases) * 100
```

See `human_review.agreement_rate()`. A lower agreement rate is not
inherently bad — it means the human-review layer is doing real work, not
rubber-stamping. What matters is that every correction is evidence-backed
and logged, which the Responsible AI dashboard tab makes visible.

## Limitations

- The mock AI diagnoser's "correct" answers are, deliberately, drawn from
  the same dataset that a real LLM would not have privileged access to —
  it demonstrates the *workflow*, not a claim that any particular model
  will reach the same conclusions on unseen data.
- The rule checker's regex-based parsing works well on the outputs
  represented in this dataset but is not a substitute for a real
  Cisco-format parser (e.g. NAPALM, Genie/pyATS) in a production tool.
- Confidence scores from the mock diagnoser are heuristic (based on whether
  the rule checker corroborated the finding), not a calibrated statistical
  measure — a live LLM's confidence is only as good as its own calibration.
