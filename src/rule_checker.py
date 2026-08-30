"""
rule_checker.py
-----------------
Deterministic, non-AI rule checker for Cisco/Packet Tracer show-command
output. This module NEVER calls an LLM — every finding here is produced by
plain regex/text parsing so it is 100% reproducible and explainable.

It is intentionally generic: it scans whatever `show_outputs` text a case
provides and looks for the patterns below wherever they occur, rather than
assuming a fixed command layout. That mirrors how a real audit script would
scrape command output pasted from many different device types.

Checks implemented (per the project brief):
  1. duplicate_ip          - the same host IP address appears more than once
  2. wrong_subnet_mask     - hosts on the same /24-ish network disagree on mask
  3. gateway_mismatch      - a host's default gateway is not any router IP seen
  4. interface_down        - an interface is administratively down / down
  5. missing_vlan          - a port references a VLAN not present in VLAN db
  6. missing_route         - routing table shows an empty/missing entry
  7. trunk_mismatch        - a VLAN is not carried on a trunk / trunk not formed
  8. missing_dhcp_pool     - a router subnet has no matching DHCP pool
  9. incorrect_dhcp_network- DHCP pool's default-router is outside its network
 10. acl_blocking          - ACL contains a deny/implicit-deny that could block traffic
 11. nat_missing           - 'ip nat inside source' exists but no inside/outside marking
 12. nat_translation_absent- NAT is configured but 0 active translations
"""
import ipaddress
import re

from utils import flatten_show_outputs

FAIL, WARN, PASS = "FAIL", "WARN", "PASS"


def _finding(check, status, severity, evidence, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "evidence": evidence.strip(),
        "message": message,
    }


def _all_text(show_outputs):
    return flatten_show_outputs(show_outputs)


# ---------------------------------------------------------------------------
# 1. Duplicate IP
# ---------------------------------------------------------------------------
def check_duplicate_ip(show_outputs):
    text = _all_text(show_outputs)
    ips = re.findall(
        r"(?:IPv4 Address|ip address)[.\s:]*\s(\d{1,3}(?:\.\d{1,3}){3})",
        text, re.IGNORECASE)
    seen = {}
    for ip in ips:
        seen[ip] = seen.get(ip, 0) + 1
    dupes = {ip: n for ip, n in seen.items() if n > 1}
    if dupes:
        ip, n = next(iter(dupes.items()))
        return _finding("duplicate_ip", FAIL, "Critical",
                         f"IP address {ip} appears {n} times in the collected evidence.",
                         f"Address {ip} is assigned to more than one device — this will "
                         "cause intermittent connectivity for both devices.")
    return _finding("duplicate_ip", PASS, "Low", "No IP address repeats in the evidence.",
                     "No duplicate IP addresses detected.")


# ---------------------------------------------------------------------------
# 2. Wrong subnet mask
# ---------------------------------------------------------------------------
_MASK_TO_PREFIX = {
    "255.255.255.0": 24, "255.255.255.128": 25, "255.255.255.192": 26,
    "255.255.255.240": 28, "255.255.255.252": 30, "255.255.0.0": 16,
}


def check_wrong_subnet_mask(show_outputs):
    text = _all_text(show_outputs)
    entries = re.findall(
        r"(\d{1,3}(?:\.\d{1,3}){3})\s*[\r\n]+.*?(?:Subnet Mask|mask)[.\s:]*\s"
        r"(\d{1,3}(?:\.\d{1,3}){3})",
        text, re.IGNORECASE | re.DOTALL)
    # group by /24 network id (first 3 octets) as a simple heuristic
    by_network = {}
    for ip, mask in entries:
        network_id = ".".join(ip.split(".")[:3])
        by_network.setdefault(network_id, set()).add(mask)

    for network_id, masks in by_network.items():
        if len(masks) > 1:
            return _finding(
                "wrong_subnet_mask", FAIL, "Medium",
                f"Hosts in the {network_id}.0/24 range report differing masks: {sorted(masks)}.",
                "One or more hosts have a subnet mask that does not match the "
                "rest of the network, which changes their calculated subnet "
                "and breaks local communication.")
    return _finding("wrong_subnet_mask", PASS, "Low",
                     "All observed hosts in each network agree on their subnet mask.",
                     "No subnet mask mismatch detected.")


# ---------------------------------------------------------------------------
# 3. Gateway mismatch
# ---------------------------------------------------------------------------
def check_gateway_mismatch(show_outputs):
    text = _all_text(show_outputs)
    gateways = re.findall(r"Default Gateway[.\s:]*\s(\d{1,3}(?:\.\d{1,3}){3})",
                           text, re.IGNORECASE)
    if not gateways:
        return _finding("gateway_mismatch", PASS, "Low",
                         "No client default-gateway entries present in this evidence.",
                         "Check not applicable to this case's evidence.")

    router_interface_pattern = re.compile(
        r"GigabitEthernet|FastEthernet|Serial\d|Vlan\d|Loopback\d|\bGi\d|\bFa\d|\bSe\d",
        re.IGNORECASE)
    if not router_interface_pattern.search(text):
        return _finding("gateway_mismatch", PASS, "Low",
                         "No router/switch interface evidence present to confirm or "
                         "deny the gateway address against.",
                         "Check not applicable to this case's evidence.")

    for gw in gateways:
        # A correctly-configured gateway address should appear again elsewhere
        # in the evidence (e.g. in 'show ip interface brief' for that router
        # interface). If it only appears once (in the client's own config),
        # no router interface actually holds that address.
        occurrences = len(re.findall(re.escape(gw), text))
        if occurrences < 2:
            return _finding(
                "gateway_mismatch", FAIL, "High",
                f"Client default gateway {gw} does not appear anywhere else in "
                "the router/switch interface evidence provided.",
                "The configured default gateway does not correspond to a "
                "real router interface, so off-subnet traffic cannot be "
                "forwarded.")
    return _finding("gateway_mismatch", PASS, "Low",
                     "Client default gateway matches a router interface IP.",
                     "No gateway mismatch detected.")


# ---------------------------------------------------------------------------
# 4. Interface down
# ---------------------------------------------------------------------------
def check_interface_down(show_outputs):
    text = _all_text(show_outputs)
    admin_down = re.findall(r"([\w./-]+)\s+[\d.]+\s+YES\s+\w+\s+administratively down",
                             text, re.IGNORECASE)
    plain_down = re.findall(r"([\w./-]+)\s+[\d.]+\s+YES\s+\w+\s+down\s+down",
                             text, re.IGNORECASE)
    err_disabled = re.findall(r"(\S+)\s+\S+\s+err-disabled", text, re.IGNORECASE)

    if admin_down:
        return _finding("interface_down", FAIL, "Critical",
                         f"Interface {admin_down[0]} status: administratively down.",
                         "This interface has been manually shut down and will "
                         "not pass any traffic until a 'no shutdown' is issued.")
    if plain_down:
        return _finding("interface_down", FAIL, "High",
                         f"Interface {plain_down[0]} status: down/down.",
                         "This interface is down (likely a physical/Layer 1 "
                         "issue such as a cable or peer-side problem).")
    if err_disabled:
        return _finding("interface_down", FAIL, "Medium",
                         f"Port {err_disabled[0]} is in err-disabled state.",
                         "The port was automatically disabled, typically by "
                         "port security or storm-control, and needs an "
                         "explicit shutdown/no shutdown to recover.")
    return _finding("interface_down", PASS, "Low",
                     "No interfaces reported as administratively down, down, or err-disabled.",
                     "No interface-down condition detected.")


# ---------------------------------------------------------------------------
# 5. Missing VLAN
# ---------------------------------------------------------------------------
def check_missing_vlan(show_outputs):
    text = _all_text(show_outputs)
    referenced = set(re.findall(r"switchport access vlan\s+(\d+)", text, re.IGNORECASE))
    referenced |= set(re.findall(r"switchport voice vlan\s+(\d+)", text, re.IGNORECASE))
    defined = set(re.findall(r"^\s*(\d+)\s+\S+.*?(?:active|suspended)", text,
                              re.IGNORECASE | re.MULTILINE))
    missing = referenced - defined
    # Only meaningful if we actually saw a VLAN database (show vlan brief) in evidence
    if "vlan brief" not in text.lower() and "vlan database" not in text.lower():
        return _finding("missing_vlan", PASS, "Low",
                         "No VLAN database evidence present in this case.",
                         "Check not applicable to this case's evidence.")
    if missing:
        vlan = sorted(missing)[0]
        return _finding("missing_vlan", FAIL, "Medium",
                         f"VLAN {vlan} is referenced by a switchport but does not "
                         f"appear as active in the VLAN database.",
                         f"VLAN {vlan} must be created (or was deleted) — a port "
                         "cannot forward traffic for a VLAN that does not exist.")
    return _finding("missing_vlan", PASS, "Low",
                     "All referenced VLANs exist in the VLAN database.",
                     "No missing VLAN detected.")


# ---------------------------------------------------------------------------
# 6. Missing route
# ---------------------------------------------------------------------------
def check_missing_route(show_outputs):
    text = _all_text(show_outputs)
    if "show ip route" not in text.lower():
        return _finding("missing_route", PASS, "Low",
                         "No routing table evidence present in this case.",
                         "Check not applicable to this case's evidence.")
    red_flags = [
        r"--\s*no entry", r"routing table is empty", r"is not advertised",
        r"not advertised into ospf",
    ]
    for pattern in red_flags:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return _finding("missing_route", FAIL, "High",
                             f"Routing table evidence: \"{m.group(0)}\".",
                             "The destination network has no route in the "
                             "routing table, so traffic to it will be dropped "
                             "or sent to the wrong next hop.")
    return _finding("missing_route", PASS, "Low",
                     "Routing table entries look present and populated.",
                     "No obviously missing route detected.")


# ---------------------------------------------------------------------------
# 7. Trunk mismatch
# ---------------------------------------------------------------------------
def check_trunk_mismatch(show_outputs):
    text = _all_text(show_outputs)
    if "trunk" not in text.lower():
        return _finding("trunk_mismatch", PASS, "Low",
                         "No trunk evidence present in this case.",
                         "Check not applicable to this case's evidence.")
    if re.search(r"no interfaces are currently in trunking", text, re.IGNORECASE):
        return _finding("trunk_mismatch", FAIL, "High",
                         "No interfaces are currently in trunking mode.",
                         "The expected inter-switch trunk never formed; check "
                         "for a mismatched 'switchport mode' on one side of "
                         "the link.")
    allowed_match = re.search(
        r"Vlans allowed on trunk\s*\n\s*\S+\s+([\d,\s]+)", text, re.IGNORECASE)
    defined_vlans = set(re.findall(r"^\s*(\d+)\s+\S+.*?active", text,
                                    re.IGNORECASE | re.MULTILINE))
    if allowed_match and defined_vlans:
        allowed = set(v.strip() for v in allowed_match.group(1).split(",") if v.strip())
        missing = defined_vlans - allowed - {"1"}
        if missing:
            vlan = sorted(missing)[0]
            return _finding("trunk_mismatch", FAIL, "High",
                             f"VLAN {vlan} exists but is not in the trunk's "
                             f"allowed list ({sorted(allowed)}).",
                             f"VLAN {vlan} is being pruned from the trunk and "
                             "cannot reach the rest of the network across it.")
    return _finding("trunk_mismatch", PASS, "Low",
                     "Trunk is formed and required VLANs are allowed.",
                     "No trunk mismatch detected.")


# ---------------------------------------------------------------------------
# 8 & 9. DHCP checks
# ---------------------------------------------------------------------------
def _dhcp_pools(text):
    pools = []
    for m in re.finditer(
            r"ip dhcp pool\s+(\S+)\s*\n(.*?)(?=\n!|\nip dhcp pool|\Z)",
            text, re.IGNORECASE | re.DOTALL):
        name, body = m.group(1), m.group(2)
        net = re.search(r"network\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})",
                         body, re.IGNORECASE)
        router = re.search(r"default-router\s+(\d{1,3}(?:\.\d{1,3}){3})", body, re.IGNORECASE)
        pools.append({
            "name": name,
            "network": net.group(1) if net else None,
            "mask": net.group(2) if net else None,
            "default_router": router.group(1) if router else None,
        })
    return pools


def check_missing_dhcp_pool(show_outputs):
    text = _all_text(show_outputs)
    router_subnets = set(
        ".".join(ip.split(".")[:3])
        for ip in re.findall(r"ip address\s+(\d{1,3}(?:\.\d{1,3}){3})", text, re.IGNORECASE)
    )
    pools = _dhcp_pools(text)
    if not pools and not router_subnets:
        return _finding("missing_dhcp_pool", PASS, "Low",
                         "No DHCP or router interface evidence present.",
                         "Check not applicable to this case's evidence.")
    pool_subnets = set(".".join(p["network"].split(".")[:3]) for p in pools if p["network"])
    if "dhcp" in text.lower():
        missing = router_subnets - pool_subnets
        # only flag if the case evidence is actually about DHCP scope for that subnet
        if missing and pools:
            subnet = sorted(missing)[0]
            return _finding("missing_dhcp_pool", FAIL, "High",
                             f"Router has an interface on {subnet}.0/24 but no "
                             "DHCP pool covers that network.",
                             f"Clients on {subnet}.0/24 have no DHCP server to "
                             "answer their requests and will self-assign an "
                             "APIPA address.")
    return _finding("missing_dhcp_pool", PASS, "Low",
                     "Every router subnet observed has a matching DHCP pool "
                     "(or DHCP is not in scope for this case).",
                     "No missing DHCP pool detected.")


def check_incorrect_dhcp_network(show_outputs):
    text = _all_text(show_outputs)
    pools = _dhcp_pools(text)
    for p in pools:
        if p["network"] and p["mask"] and p["default_router"]:
            try:
                net = ipaddress.ip_network(f"{p['network']}/{p['mask']}", strict=False)
                if ipaddress.ip_address(p["default_router"]) not in net:
                    return _finding(
                        "incorrect_dhcp_network", FAIL, "High",
                        f"Pool '{p['name']}': network {p['network']}/{p['mask']} "
                        f"but default-router {p['default_router']} is outside it.",
                        "Clients will receive a valid IP/mask but an "
                        "unreachable default gateway from this pool.")
            except ValueError:
                continue
    if not pools:
        return _finding("incorrect_dhcp_network", PASS, "Low",
                         "No DHCP pool evidence present in this case.",
                         "Check not applicable to this case's evidence.")
    return _finding("incorrect_dhcp_network", PASS, "Low",
                     "Every DHCP pool's default-router falls inside its own network.",
                     "No incorrect DHCP network/default-router detected.")


# ---------------------------------------------------------------------------
# 10. ACL blocking
# ---------------------------------------------------------------------------
def check_acl_blocking(show_outputs):
    text = _all_text(show_outputs)
    if "access list" not in text.lower() and "access-list" not in text.lower():
        return _finding("acl_blocking", PASS, "Low",
                         "No ACL evidence present in this case.",
                         "Check not applicable to this case's evidence.")
    deny_lines = re.findall(r"\bdeny\b.*", text, re.IGNORECASE)
    if deny_lines:
        return _finding("acl_blocking", WARN, "High",
                         f"ACL contains an explicit deny statement: "
                         f"\"{deny_lines[0].strip()}\".",
                         "An explicit deny is present — confirm it is not "
                         "unintentionally blocking legitimate traffic for the "
                         "affected source.")

    # The "always end with permit ip any any, or the implicit deny will bite
    # you" convention only applies to EXTENDED named/numbered ACLs used for
    # traffic filtering. Standard ACLs (e.g. those referenced by
    # 'ip nat inside source list <n>' or VTY access-classes) use a different
    # syntax and are frequently, intentionally, permit-only — flagging them
    # here would be a false positive, so we only apply this heuristic when
    # the evidence actually shows an Extended ACL.
    is_extended_acl = re.search(r"Extended IP access list", text, re.IGNORECASE)
    has_permit_any = re.search(r"permit\s+ip\s+any\s+any", text, re.IGNORECASE)
    if is_extended_acl and not has_permit_any:
        return _finding("acl_blocking", WARN, "Medium",
                         "Extended ACL has permit statements but no trailing "
                         "'permit ip any any'.",
                         "Traffic that does not match an earlier permit line "
                         "will hit the implicit deny at the end of the ACL.")
    return _finding("acl_blocking", PASS, "Low",
                     "ACL evidence does not show an obviously blocking rule.",
                     "No ACL blocking condition detected.")


# ---------------------------------------------------------------------------
# 11 & 12. NAT checks
# ---------------------------------------------------------------------------
def check_nat_missing(show_outputs):
    text = _all_text(show_outputs)
    if "ip nat inside source" not in text.lower():
        return _finding("nat_missing", PASS, "Low",
                         "No 'ip nat inside source' statement present in this case.",
                         "Check not applicable to this case's evidence.")
    has_inside = re.search(r"\bip nat inside\b(?!\s+source)", text, re.IGNORECASE)
    has_outside = re.search(r"\bip nat outside\b", text, re.IGNORECASE)
    if not (has_inside and has_outside):
        missing_side = "inside" if not has_inside else "outside"
        return _finding("nat_missing", FAIL, "High",
                         f"'ip nat {missing_side}' marking not found on any interface.",
                         "NAT translation rules exist, but the "
                         f"{missing_side} interface was never marked with "
                         f"'ip nat {missing_side}', so NAT never triggers.")
    return _finding("nat_missing", PASS, "Low",
                     "Both 'ip nat inside' and 'ip nat outside' markings are present.",
                     "NAT interface configuration looks complete.")


def check_nat_translation_absent(show_outputs):
    text = _all_text(show_outputs)
    m = re.search(r"Total active translations:\s*(\d+)", text, re.IGNORECASE)
    if not m:
        return _finding("nat_translation_absent", PASS, "Low",
                         "No 'show ip nat statistics' evidence present in this case.",
                         "Check not applicable to this case's evidence.")
    count = int(m.group(1))
    if count == 0:
        return _finding("nat_translation_absent", FAIL, "High",
                         "Total active translations: 0.",
                         "NAT is configured but has never actually translated a "
                         "packet — look for an ACL, interface marking, or "
                         "wrong-interface problem preventing NAT from matching "
                         "traffic.")
    return _finding("nat_translation_absent", PASS, "Low",
                     f"Total active translations: {count}.",
                     "NAT is actively translating traffic.")


CHECKS = [
    check_duplicate_ip,
    check_wrong_subnet_mask,
    check_gateway_mismatch,
    check_interface_down,
    check_missing_vlan,
    check_missing_route,
    check_trunk_mismatch,
    check_missing_dhcp_pool,
    check_incorrect_dhcp_network,
    check_acl_blocking,
    check_nat_missing,
    check_nat_translation_absent,
]


def run_all_checks(case):
    """Run every deterministic rule against a case's show_outputs.
    Returns the full list of findings (PASS/WARN/FAIL for each check)."""
    show_outputs = case["show_outputs"] if isinstance(case, dict) else case
    return [check(show_outputs) for check in CHECKS]


def failing_findings(case):
    return [f for f in run_all_checks(case) if f["status"] in (FAIL, WARN)]


if __name__ == "__main__":
    # Small demo: run the checker against CASE-007 (gateway mismatch)
    from case_loader import load_cases, get_case_by_id
    import json as _json

    case = get_case_by_id("CASE-007", load_cases())
    print(f"Rule checker results for {case['case_id']}: {case['symptom']}\n")
    for finding in run_all_checks(case):
        print(_json.dumps(finding, indent=2))
