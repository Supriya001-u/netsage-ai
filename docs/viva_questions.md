# NetSage AI — Viva Preparation

Concise, memorable answers to likely viva questions.

**Q: What problem does NetSage AI solve?**
It helps a junior engineer diagnose Cisco/Packet Tracer network faults
faster by combining a deterministic rule checker with an AI that reasons
over command-output evidence — while keeping a human in control of every
decision.

**Q: Why use AI at all, if a rule checker already exists?**
The rule checker only catches structural problems it was explicitly coded
to look for (a shutdown interface, a missing VLAN). Many real symptoms —
DHCP exhaustion vs. outage, wireless interference, DNS server choice —
need judgement over evidence in natural language, which is where the AI
adds value the rule checker cannot.

**Q: Why is human review required?**
Because AI diagnoses can be plausible but wrong (see the 5 documented
cases in `data/responsible_ai_log.csv`), and network changes have real
consequences. NetSage AI treats the AI as a decision-support tool, never
an autonomous agent — nothing is ever auto-applied.

**Q: What is the OSI model?**
A 7-layer conceptual model (Physical, Data Link, Network, Transport,
Session, Presentation, Application) describing how network communication
is broken into layers, each responsible for a specific function.

**Q: Why are VLAN issues Layer 2?**
VLANs segment a broadcast domain at the switching/frame-forwarding level —
that's Data Link layer (Layer 2) functionality, before IP routing is ever
involved.

**Q: Why are routing issues Layer 3?**
Routing decides how IP packets move between different networks based on
IP addresses — that's the Network layer's job (Layer 3).

**Q: What is an ACL?**
An Access Control List — an ordered list of permit/deny rules a router or
switch evaluates top-to-bottom to decide whether to allow or block
traffic matching certain criteria (source/destination IP, port, protocol).

**Q: What is NAT?**
Network Address Translation — rewrites private internal IP addresses to a
public IP (often with port translation/PAT) so internal hosts can reach
the Internet using a shared public address.

**Q: What does DHCP do?**
Dynamic Host Configuration Protocol automatically assigns an IP address,
subnet mask, default gateway, and DNS server to a client when it joins
the network, instead of requiring manual configuration.

**Q: What does DNS do?**
Domain Name System — resolves human-readable hostnames (e.g.
`fileserver.corp.local`) into IP addresses that devices actually use to
communicate.

**Q: Why use a rule-based checker at all if you have an LLM?**
Because it's 100% deterministic and reproducible — the same input always
gives the same output, with no API cost, no hallucination risk, and no
dependency on an external service. It's the safety net the AI's more
flexible reasoning sits on top of.

**Q: What's the difference between deterministic rules and AI reasoning?**
Rules check for exact, pre-defined patterns (a specific text string or
value) and always give the same answer. AI reasoning can weigh multiple
plausible explanations, cite evidence in natural language, and handle
symptoms nobody explicitly coded a check for — but it can also be
confidently wrong, which is why it's paired with mandatory human review.

**Q: How does the AI use evidence?**
It is prompted (see `prompts/diagnose_prompt.md`) to cite specific lines
from the `show_outputs` provided, and is explicitly forbidden from
inventing evidence it wasn't given.

**Q: What is confidence, in this system?**
A 0–100 score the AI assigns reflecting how strongly the given evidence
supports its stated root cause — high when the evidence is direct and
unambiguous, low when evidence is only suggestive or a key piece is
missing.

**Q: Why should AI not automatically apply network fixes?**
Because a wrong or incomplete diagnosis acted on automatically could cause
an outage, security exposure, or data loss. Human review adds a
judgement/accountability layer AI models cannot yet reliably provide.

**Q: What is responsible AI (in this project's context)?**
Building AI systems whose outputs are transparent (evidence-cited),
calibrated (confidence reflects real certainty), and never
autonomous-by-default — paired with documented, honest tracking of when
the AI is wrong (see `docs/responsible_ai.md`).

**Q: How is AI-human agreement calculated?**
`(number of ACCEPT decisions) / (total reviewed cases) * 100`, computed in
`human_review.agreement_rate()`. It measures how often the human reviewer
found the AI's original diagnosis correct enough to accept as-is.

**Q: What happens when the AI is wrong?**
The reviewer chooses EDIT (partially right, needs correction) or REJECT
(unsupported by evidence), must supply a corrected diagnosis and a reason,
and that becomes the final logged diagnosis — never the AI's original
answer.

**Q: What are the project's limitations?**
The rule checker's regex parsing is tuned to this dataset's evidence
format rather than being a full production-grade CLI parser; the mock AI
mode demonstrates the workflow rather than claiming any particular live
LLM will reach identical conclusions on unseen data; and the dataset,
while realistic, is Packet-Tracer-scale rather than an enterprise network.

---

## Additional Q&A (audit pass — Phase 14 additions)

**Q: Why not use only deterministic rules?**
Rules can only catch problems someone explicitly anticipated and coded a
pattern for. Many real symptoms — DHCP pool exhaustion vs. an outage,
wireless channel interference, which DNS server is "correct" for a given
VLAN — need judgement over evidence in natural language. A pure rule-based
system would either miss these entirely or need an ever-growing, brittle
list of special cases.

**Q: Why not use only AI?**
An LLM can sound confident while being wrong (see the 5 cases in
`data/responsible_ai_log.csv`), and its output isn't perfectly
reproducible. A deterministic rule checker gives a small set of findings
that are 100% reliable and explainable every single time, with no API cost
and no hallucination risk — a safety net the AI's reasoning sits on top of.

**Q: Why use both rules and AI together?**
Because they cover each other's blind spots: rules give reliable,
reproducible findings for problems they were coded to look for; AI reasons
over evidence for everything else. Rule-checker findings are also passed
to the AI as extra corroborating context, so the AI's confidence is higher
when a deterministic check already agrees with it.

**Q: What is human-in-the-loop AI?**
An AI workflow where a human reviewer must examine and approve (or correct)
every AI output before it is considered final or acted upon — as opposed
to a fully autonomous system that acts on its own conclusions. NetSage AI
is human-in-the-loop by design: `needs_human_review` is always `true`, and
`human_review.py` will not silently accept a diagnosis.

**Q: How is confidence calculated?**
In mock mode, confidence is a simple heuristic: it starts higher when the
deterministic rule checker independently corroborates the same finding,
and lower when there's no such corroboration — it is not a statistical
probability. In live LLM mode, confidence is whatever score the model
itself reports, guided by the calibration bands described in
`prompts/diagnose_prompt.md` (evidence that directly and unambiguously
shows the fault scores high; evidence that is merely suggestive or
incomplete scores low). Either way, confidence is meant to reflect how
strongly the *given evidence* supports the conclusion, not how "smart" the
model feels.

**Q: What is inter-VLAN routing?**
The process of routing IP traffic between different VLANs (different
Layer-2 broadcast domains), typically done by a Layer-3 device — either a
multilayer switch or a router using sub-interfaces ("router-on-a-stick"),
as modeled by R1's `Gi0/0.10`, `Gi0/0.20`, etc. in this project's dataset.

**Q: What is a routing table?**
A table maintained by a router listing known destination networks and the
next hop / exit interface to reach each one, built from directly connected
networks, static routes, and/or a dynamic routing protocol such as OSPF.
`show ip route` displays it; a destination with no matching entry is
unreachable, which is exactly what several "missing route" cases in the
dataset demonstrate.

**Q: Why is a particular issue associated with Layer 2 vs. Layer 3 vs. Layer 4?**
Match the fault to the layer whose job was actually broken: switching /
VLAN / frame-forwarding problems are Layer 2; IP addressing and routing
decisions are Layer 3; port-based filtering and session-level concerns
(like a specific TCP port being blocked) are Layer 4. A single symptom can
span layers — e.g. a Layer 1 physical shutdown can produce a Layer 3
routing symptom — which is why each case in this project states the
specific OSI layer(s) its root cause actually sits at.

**Q: Why is deterministic validation important in an AI system like this?**
Because it provides a small set of ground-truth findings that never
hallucinate and never vary between runs, which both (a) helps catch
obvious structural misconfigurations immediately and cheaply, and (b)
gives the AI (and the human reviewer) independent corroborating evidence
to check its own reasoning against, rather than relying on the AI's
narrative alone.
