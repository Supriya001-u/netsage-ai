"""
ai_diagnoser.py
-----------------
Isolates all AI/LLM integration behind a single diagnose(case, rule_findings)
function.

Two modes, controlled by the MOCK_MODE environment variable (see .env.example):

  MOCK_MODE=true  (default, no API key needed)
    Returns a deterministic, evidence-grounded diagnosis built from the
    case's own data. A small, explicitly-labelled set of cases
    (KNOWN_AI_MISTAKES) intentionally returns a plausible-but-wrong
    diagnosis, matching the Responsible AI log in data/responsible_ai_log.csv
    and docs/responsible_ai.md. This lets the full review workflow be
    demonstrated end-to-end without any external API access.

  MOCK_MODE=false
    Calls the real Anthropic API (model claude-sonnet-4-6) using the
    system prompt in prompts/diagnose_prompt.md and the worked examples in
    prompts/few_shot_examples.md, and parses the structured JSON response.

Either way, the function ALWAYS sets needs_human_review = True. No caller
in this codebase is allowed to skip human review based on confidence.
"""
import os
import re

from utils import PROMPTS_DIR, flatten_show_outputs, safe_json_parse

MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() != "false"
ANTHROPIC_MODEL = "claude-sonnet-4-6"

REQUIRED_FIELDS = [
    "root_cause", "confidence", "osi_layer", "evidence", "next_command",
    "fix_steps", "severity", "concept", "needs_human_review",
]

# ---------------------------------------------------------------------------
# Category -> (next_command, fix_steps template) used to build realistic
# mock diagnoses without hard-coding a full answer for every one of the 35
# cases individually.
# ---------------------------------------------------------------------------
CATEGORY_TEMPLATES = {
    "vlan": {
        "next_command": "show vlan brief",
        "fix_steps": [
            "Confirm the intended VLAN assignment with the network design/topology document.",
            "Correct the access VLAN, trunk allowed-list, or VLAN database entry as needed.",
            "Re-run 'show vlan brief' and 'show interfaces trunk' to confirm the change.",
            "Have the affected host re-test connectivity.",
        ],
    },
    "gateway": {
        "next_command": "show ip interface brief",
        "fix_steps": [
            "Verify the intended gateway IP address for this subnet against the design document.",
            "Correct the mismatched client configuration or bring up the gateway interface as needed.",
            "Re-run 'show ip interface brief' to confirm the interface is up/up with the correct IP.",
            "Re-test off-subnet connectivity from an affected host.",
        ],
    },
    "dhcp": {
        "next_command": "show ip dhcp pool",
        "fix_steps": [
            "Review the DHCP pool's network, default-router, and exclusion configuration.",
            "Correct the pool definition or add the missing pool for the affected subnet.",
            "Release and renew a test client's lease to confirm the fix.",
            "Monitor 'show ip dhcp pool' utilization to catch future exhaustion early.",
        ],
    },
    "dns": {
        "next_command": "show running-config | section dns",
        "fix_steps": [
            "Confirm the correct internal/external DNS server address(es) for this network.",
            "Correct the DHCP-distributed or statically-configured DNS server entry.",
            "Test with nslookup from an affected host after the change.",
            "Document the approved DNS server addresses to avoid recurrence.",
        ],
    },
    "routing": {
        "next_command": "show ip route",
        "fix_steps": [
            "Confirm the intended routing design (static vs. dynamic) for the affected network.",
            "Add the missing route, network statement, or correct the erroneous next hop.",
            "Re-run 'show ip route' on the affected router(s) to confirm the entry appears.",
            "Re-test end-to-end connectivity and run a traceroute to confirm the path.",
        ],
    },
    "acl": {
        "next_command": "show access-lists",
        "fix_steps": [
            "Review the full ACL top-to-bottom, noting that ACLs are evaluated in order.",
            "Add a more specific permit statement above the blocking deny, rather than removing the deny.",
            "Apply the corrected ACL and re-test the affected traffic.",
            "Document the change and the business reason it was approved.",
        ],
    },
    "nat": {
        "next_command": "show ip nat statistics",
        "fix_steps": [
            "Confirm 'ip nat inside' and 'ip nat outside' are applied to the correct interfaces.",
            "Confirm the ACL referenced by 'ip nat inside source list' actually permits the intended traffic.",
            "Clear existing translations ('clear ip nat translation *') and generate new test traffic.",
            "Re-run 'show ip nat translations' to confirm active entries appear.",
        ],
    },
    "wireless": {
        "next_command": "show running-config",
        "fix_steps": [
            "Review the SSID's security/authentication configuration for internal consistency.",
            "Correct the wireless configuration (security mode, bridge-group, channel, or broadcast setting).",
            "Have a test device attempt to associate and confirm it receives a valid DHCP address.",
            "Document the corrected configuration for the AP/WLC template.",
        ],
    },
}


def _category_for(case):
    canonical = case.get("category")
    if canonical and canonical in CATEGORY_TEMPLATES:
        return canonical
    # Fallback for any case data that predates the explicit 'category' field.
    text = (case["concept"] + " " + case["expected_fault"] + " " + case["symptom"]).lower()
    for cat in CATEGORY_TEMPLATES:
        if cat in text:
            return cat
    return "routing"  # sensible generic default


def _pick_evidence_lines(case, n=2):
    text = flatten_show_outputs(case["show_outputs"])
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("$")]

    patterns = [
        r"err-disabled",
        r"administratively down",
        r"default-router\s+\d",
        r"Default Gateway\s*\.",
        r"is not advertised",
        r"-- no entry",
        r"routing table is empty",
        r"10 deny\s+",
        r"\bdeny\b",
        r"Total active translations:\s*\d+",
        r"Vlans allowed on trunk",
        r"ip nat inside source list",
        r"guest-mode disabled",
        r"Channel:\s*\d+",
        r"bridge-group\s+\d+",
        r"authentication open",
        r"switchport access vlan\s+\d+",
        r"10 permit tcp\s+",
        r"DNS Servers\s*\.\s*\.\s*:\s*0\.0\.0\.0",
        r"Server failed",
        r"Leased addresses\s*:\s*\d+",
        r"ip access-group\s+",
        r"no interfaces are currently in trunking",
    ]

    selected = []
    for pat in patterns:
        for line in lines:
            if re.search(pat, line, re.IGNORECASE):
                if line not in selected:
                    selected.append(line)
                if len(selected) >= n:
                    return selected

    data_lines = [l for l in lines if not re.match(r"^-+$", l) and not l.startswith("Port") and not l.startswith("VLAN Name")]
    for line in data_lines:
        if line not in selected:
            selected.append(line)
        if len(selected) >= n:
            return selected

    return selected if selected else lines[:n]


# ---------------------------------------------------------------------------
# Deliberately-wrong mock diagnoses, matching data/responsible_ai_log.csv.
# Keyed by case_id. Confidence is kept moderate (never 90+) because these
# represent the AI being plausible but not certain -- exactly the situation
# where human review earns its keep.
# ---------------------------------------------------------------------------
KNOWN_AI_MISTAKES = {
    "CASE-025": {
        "root_cause": "R1's routing table is missing a route to the 192.168.30.0/24 server subnet.",
        "confidence": 64,
        "osi_layer": "Layer 3 (Network)",
        "evidence": ["No route to 192.168.30.0/24 was confirmed in the routing table evidence provided."],
        "next_command": "show ip route",
        "fix_steps": [
            "Verify OSPF/static routing configuration for the 192.168.30.0/24 subnet.",
            "Add a route or network statement if missing.",
        ],
        "severity": "High",
        "concept": "Possible missing route",
    },
    "CASE-012": {
        "root_cause": "The DHCP server process on R1 has stopped responding to requests on VLAN 20.",
        "confidence": 58,
        "osi_layer": "Application (DHCP service)",
        "evidence": ["Some PCs on VLAN 20 are not receiving DHCP leases."],
        "next_command": "show ip dhcp server statistics",
        "fix_steps": [
            "Restart the DHCP service on R1.",
            "Confirm the DHCP pool is still bound to the correct interface.",
        ],
        "severity": "Medium",
        "concept": "Possible DHCP service failure",
    },
    "CASE-004": {
        "root_cause": "SW2's Gi0/1 access VLAN is mismatched with SW1's Gi0/2, causing the VLAN 10 outage.",
        "confidence": 61,
        "osi_layer": "Layer 2 (Data Link)",
        "evidence": ["Gi0/2 on SW1 is an access port for VLAN 10; assumed SW2 side differs."],
        "next_command": "show running-config interface Gi0/1 (on SW2)",
        "fix_steps": [
            "Set SW2's Gi0/1 access VLAN to match SW1's Gi0/2 (VLAN 10).",
            "Verify VLAN 10 connectivity between the switches.",
        ],
        "severity": "High",
        "concept": "Possible VLAN mismatch between switches",
    },
    "CASE-008": {
        "root_cause": "VLAN 20 clients cannot resolve DNS names, causing the reported loss of connectivity.",
        "confidence": 55,
        "osi_layer": "Application (Layer 7)",
        "evidence": ["Clients on VLAN 20 report being unable to reach other networks."],
        "next_command": "nslookup from an affected VLAN 20 host",
        "fix_steps": [
            "Verify the DNS server address handed out to VLAN 20 clients.",
            "Update the DHCP pool's dns-server entry if incorrect.",
        ],
        "severity": "Medium",
        "concept": "Possible DNS misconfiguration",
    },
    "CASE-028": {
        "root_cause": "NAT overload (PAT) is not enabled on R1's outside interface.",
        "confidence": 66,
        "osi_layer": "Layer 3 (Network)",
        "evidence": ["'show ip nat translations' shows no active translations."],
        "next_command": "show running-config | section nat",
        "fix_steps": [
            "Re-apply 'ip nat inside source list NAT_SRC interface GigabitEthernet0/1 overload'.",
            "Confirm 'ip nat inside' / 'ip nat outside' are present on the correct interfaces.",
        ],
        "severity": "High",
        "concept": "Possible missing NAT overload configuration",
    },
}


def _build_mock_diagnosis(case, rule_findings):
    if case["case_id"] in KNOWN_AI_MISTAKES:
        d = dict(KNOWN_AI_MISTAKES[case["case_id"]])
        d["needs_human_review"] = True
        return d

    category = _category_for(case)
    template = CATEGORY_TEMPLATES[category]
    evidence = _pick_evidence_lines(case)

    failing = [f for f in rule_findings if f["status"] in ("FAIL", "WARN")]
    if failing:
        confidence = 88 + min(8, len(failing))  # corroborated by the rule checker
    else:
        confidence = 68  # no deterministic corroboration -> a bit less certain

    return {
        "root_cause": case["expected_fault"],
        "confidence": min(confidence, 96),
        "osi_layer": case["osi_layer"],
        "evidence": evidence,
        "next_command": template["next_command"],
        "fix_steps": template["fix_steps"],
        "severity": case["severity"],
        "concept": case["concept"],
        "needs_human_review": True,
    }


def _mock_diagnose(case, rule_findings):
    diagnosis = _build_mock_diagnosis(case, rule_findings)
    diagnosis["_source"] = "mock"
    return diagnosis


# ---------------------------------------------------------------------------
# Live LLM path (isolated here per the brief's requirement)
# ---------------------------------------------------------------------------
def _load_prompt_text():
    with open(os.path.join(PROMPTS_DIR, "diagnose_prompt.md"), "r", encoding="utf-8") as f:
        diagnose_prompt = f.read()
    with open(os.path.join(PROMPTS_DIR, "few_shot_examples.md"), "r", encoding="utf-8") as f:
        few_shot = f.read()
    return diagnose_prompt, few_shot


LIVE_LLM_TIMEOUT_SECONDS = 30


def _live_diagnose(case, rule_findings):
    """Calls the real Anthropic API. Requires ANTHROPIC_API_KEY in the
    environment (see .env.example). Kept import-local so the rest of the
    app works even if the 'anthropic' package is not installed in mock mode.

    Raises on failure (missing key, network/API error, malformed response);
    diagnose() below is responsible for catching these and returning a
    graceful fallback diagnosis instead of crashing the caller.
    """
    import anthropic  # local import: only required when MOCK_MODE=false

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MOCK_MODE=false but ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key, or set MOCK_MODE=true."
        )

    diagnose_prompt, few_shot = _load_prompt_text()
    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        f"{few_shot}\n\n---\n\nNow diagnose this new case.\n\n"
        f"Symptom:\n{case['symptom']}\n\n"
        f"Topology note:\n{case['topology_note']}\n\n"
        f"Evidence (show command output):\n{flatten_show_outputs(case['show_outputs'])}\n\n"
        f"Deterministic rule-checker findings:\n{rule_findings}\n\n"
        "Diagnose the most likely root cause and respond with ONLY the "
        "required JSON object."
    )

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1000,
            system=diagnose_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=LIVE_LLM_TIMEOUT_SECONDS,
        )
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API error: {e}") from e
    except Exception as e:  # network errors, timeouts, etc.
        raise RuntimeError(f"Could not reach the Anthropic API: {e}") from e

    text = "".join(block.text for block in response.content if block.type == "text")
    parsed = safe_json_parse(text)
    if not parsed:
        raise ValueError(f"Could not parse a JSON diagnosis from the model response:\n{text}")
    parsed["needs_human_review"] = True  # enforced regardless of what the model returned
    parsed["_source"] = "live_llm"
    return parsed


def _fallback_diagnosis(case, error):
    """Returned by diagnose() when live-mode AI diagnosis fails for any
    reason (missing key, API error, malformed response, network/timeout).
    Keeps the schema intact and forces human review, rather than letting
    an exception crash the CLI or dashboard."""
    return {
        "root_cause": f"AI diagnosis unavailable ({error}). Manual review required.",
        "confidence": 0,
        "osi_layer": case.get("osi_layer", "Unknown"),
        "evidence": ["AI diagnosis could not be generated for this case."],
        "next_command": "Retry, check ANTHROPIC_API_KEY / network connectivity, "
        "or set MOCK_MODE=true.",
        "fix_steps": [
            "This is a system error, not a network fix — no diagnosis was produced.",
            "Verify .env / ANTHROPIC_API_KEY is set correctly if using live mode.",
            "Check network connectivity to api.anthropic.com.",
            "As a fallback, set MOCK_MODE=true to continue the review workflow offline.",
        ],
        "severity": case.get("severity", "Unknown"),
        "concept": case.get("concept", "Unknown"),
        "needs_human_review": True,
        "_source": "error_fallback",
    }


def diagnose(case, rule_findings=None):
    """Main entry point used by main.py / dashboard.py. Always returns a
    dict matching REQUIRED_FIELDS, and always with needs_human_review=True.
    In live mode, any failure (missing API key, API error, malformed JSON,
    network/timeout) is caught here and turned into a graceful fallback
    diagnosis rather than an unhandled exception."""
    rule_findings = rule_findings or []
    if MOCK_MODE:
        result = _mock_diagnose(case, rule_findings)
    else:
        try:
            result = _live_diagnose(case, rule_findings)
        except Exception as e:
            result = _fallback_diagnosis(case, e)

    for field in REQUIRED_FIELDS:
        if field not in result:
            raise ValueError(f"AI diagnosis is missing required field: {field}")
    return result


if __name__ == "__main__":
    from case_loader import load_cases, get_case_by_id
    from rule_checker import run_all_checks
    import json

    case = get_case_by_id("CASE-025", load_cases())
    findings = run_all_checks(case)
    print(json.dumps(diagnose(case, findings), indent=2))
