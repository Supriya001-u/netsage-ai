# NetSage AI — Demo Script (5–10 minutes)

**Demo case: `CASE-025`** — a PC can ping its gateway but cannot reach a file
server in another VLAN, while other VLANs can. The real cause is an ACL
`deny` line; NetSage AI's mock diagnoser is deliberately seeded to first
suggest a routing problem instead (see `ai_diagnoser.KNOWN_AI_MISTAKES` and
`data/responsible_ai_log.csv`). This case is the strongest demo choice
because:

- the symptom is genuinely ambiguous (could look like routing, ACL, or a
  server-side problem from the ticket alone);
- the rule checker produces a concrete, useful `acl_blocking` finding;
- the AI's first answer is plausible but wrong, so human review visibly
  does real work, not a rubber stamp;
- the fix (add a specific permit line above the deny) is easy to explain
  and verify.

Run:
```bash
python3 src/main.py --case CASE-025
```

## Timed flow (10 minutes)

### 0:00–1:00 — Problem statement
> "NetSage AI helps diagnose Cisco/Packet Tracer network faults by
> combining a deterministic, non-AI rule checker with an AI that reasons
> over evidence — and it never applies a fix automatically. Every
> diagnosis has to be Accepted, Edited, or Rejected by a human."

### 1:00–2:00 — Architecture
Show the pipeline diagram from `docs/architecture.md`:
```
Case selection -> Rule checker -> AI diagnosis -> Evidence comparison ->
Human review (Accept/Edit/Reject) -> Final diagnosis -> Dashboard/logging
```
Emphasize the rule checker and AI are independent — the rule checker is
never replaced by the AI, it runs first and its findings are passed to the
AI as extra context.

### 2:00–3:00 — Select the broken case
```bash
python3 src/main.py --case CASE-025
```
Read the symptom aloud: PC can ping its gateway, but cannot reach the file
server SVR1 in VLAN 30, while other VLANs can reach it fine. Point out this
already rules out basic Layer 1/2 problems on the reporting PC.

### 3:00–4:00 — Show network evidence
Show `show access-lists` and the ACL applied to the server's sub-interface.
Point out the three ACL lines — this is the *only* evidence the system is
allowed to reason from (no invented data allowed, per
`prompts/diagnose_prompt.md`).

### 4:00–5:00 — Run the rule checker
Point out the `acl_blocking` finding (WARN, High severity) that fires with
zero AI/LLM calls — pure regex parsing over the evidence, 100% reproducible
every time. Contrast with the ~46% of cases in the dataset where no
deterministic rule fires at all (see `docs/architecture.md` §2) — this is
one of the cases where the checker earns its keep.

### 5:00–6:00 — Show the AI diagnosis
Show the AI's structured JSON output. Its root cause is: *"R1's routing
table is missing a route to the 192.168.30.0/24 server subnet"* — plausible
sounding, moderate confidence (64%), but **wrong**. Point out it still
cites evidence and still sets `needs_human_review: true`.

### 6:00–7:00 — Human review
Walk through why the AI's explanation sounds reasonable at first glance,
then show the actual evidence that contradicts it: `show access-lists`
line 20 is an explicit `deny` for the exact reporting subnet
(192.168.10.0/24) to the server. Enter an **EDIT** decision with the
corrected diagnosis and the specific evidence line as the reason. Say
explicitly: **"No fix is ever applied automatically — only a human
reviewer can finalize a diagnosis."**

### 7:00–8:00 — Explain the fix
The recommended fix (from `fix_steps`) is to add a more specific `permit`
line above the blocking `deny`, never to delete the deny outright, and to
get the change approved before applying it to a real device.

### 8:00–9:00 — Verify
Show the final diagnosis now stored is the reviewer's corrected version,
not the AI's original text, and that it's persisted to
`outputs/review_log.json`. Optionally re-run `python3 src/main.py --list`
or open the dashboard's Case Detail tab on CASE-025 to show the same
result end-to-end in the UI.

### 9:00–10:00 — Responsible AI + conclusion
Open `streamlit run src/dashboard.py` → **Responsible AI** tab. Show the
5-row log, including this exact CASE-025 correction, each with a different
failure mode (routing-vs-ACL, DHCP outage-vs-exhaustion, VLAN-vs-trunk,
DNS-vs-gateway, NAT-vs-blocking-ACL). Close with:

> "NetSage AI never auto-applies a network change. It pairs a
> deterministic rule checker for structural misconfigurations with an AI
> that reasons over evidence for the softer cases — and every diagnosis,
> regardless of confidence, requires a human to Accept, Edit, or Reject it
> before it's final."

## Companion "AI is wrong" cases for follow-up questions

If asked "what if the AI is wrong in a different way?", these four are
ready to run and each demonstrate a different mistake pattern:

```bash
python3 src/main.py --case CASE-004   # AI: VLAN mismatch  -> Real: trunk not formed
python3 src/main.py --case CASE-008   # AI: DNS problem    -> Real: gateway interface down
python3 src/main.py --case CASE-012   # AI: DHCP outage    -> Real: DHCP pool exhaustion
python3 src/main.py --case CASE-028   # AI: NAT missing    -> Real: ACL blocks NAT'd traffic
```

## Why this demo case is a good choice for a viva

It shows all three layers working together (deterministic check, AI
reasoning, human correction) on a single, well-understood case, and the
four companion cases each give a distinct, ready answer for "what if the
AI is wrong?" follow-ups covering VLAN/trunk, DNS/gateway, DHCP
outage/exhaustion, and NAT/ACL confusion.
