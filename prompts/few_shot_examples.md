# Few-Shot Worked Examples for NetSage AI

These three examples are included ahead of the real case in the prompt sent
to the LLM (see `diagnose_prompt.md`). They teach the model the expected
evidence-citation style and confidence calibration. They mirror the same
JSON schema the model must return for real cases.

---

## Example 1 — Confident, single clear cause

**Symptom:** All PCs on VLAN 20 lost access to every other network at the
same time; local VLAN 20 communication still works.

**Evidence:**
```
show ip interface brief (R1)
Interface              IP-Address      OK? Method Status                    Protocol
GigabitEthernet0/0.20  192.168.20.1    YES manual administratively down     down
```

**Expected response:**
```json
{
  "root_cause": "Gateway sub-interface Gi0/0.20 on R1 has been administratively shut down.",
  "confidence": 97,
  "osi_layer": "Layer 1/3 (Physical / Network)",
  "evidence": [
    "show ip interface brief (R1) shows GigabitEthernet0/0.20 status as 'administratively down'"
  ],
  "next_command": "show running-config interface GigabitEthernet0/0.20",
  "fix_steps": [
    "Confirm with the network owner that the sub-interface should be active.",
    "Enter interface configuration mode for GigabitEthernet0/0.20 and run 'no shutdown'.",
    "Re-run 'show ip interface brief' to confirm status changes to up/up.",
    "Have the affected VLAN 20 users re-test connectivity to other VLANs."
  ],
  "severity": "Critical",
  "concept": "Gateway interface administratively down",
  "needs_human_review": true
}
```

---

## Example 2 — Moderate confidence, evidence points one way but is not exhaustive

**Symptom:** PC gets an IP address and can ping its gateway, but cannot
reach the file server SVR1 (192.168.30.50) in VLAN 30, while other VLANs
can.

**Evidence:**
```
show access-lists
Extended IP access list SERVER_ACL
    10 permit tcp 192.168.20.0 0.0.0.255 host 192.168.30.50 eq 80
    20 deny ip 192.168.10.0 0.0.0.255 host 192.168.30.50
    30 permit ip any any
```

**Expected response:**
```json
{
  "root_cause": "ACL 'SERVER_ACL' applied inbound on the server VLAN explicitly denies traffic from the 192.168.10.0/24 subnet to SVR1.",
  "confidence": 78,
  "osi_layer": "Layer 3/4 (Network/Transport)",
  "evidence": [
    "show access-lists line 20: 'deny ip 192.168.10.0 0.0.0.255 host 192.168.30.50'",
    "The reporting PC's subnet was not confirmed in the evidence provided, so this assumes it is in 192.168.10.0/24"
  ],
  "next_command": "show ip interface brief | include 192.168.10",
  "fix_steps": [
    "Confirm the reporting PC's IP address is actually in 192.168.10.0/24.",
    "If confirmed, review with the network owner whether VLAN 10 access to SVR1 should be permitted.",
    "If access should be allowed, add a specific permit line above the deny statement rather than removing the deny outright.",
    "Re-test connectivity from a VLAN 10 host after the change is approved and applied."
  ],
  "severity": "High",
  "concept": "ACL explicit deny blocking legitimate traffic",
  "needs_human_review": true
}
```

---

## Example 3 — Low confidence, evidence insufficient

**Symptom:** A specific PC cannot resolve any hostname while every other PC
on the same VLAN resolves names normally.

**Evidence:**
```
PC ipconfig
IPv4 Address. . . . . . . . . . : 192.168.10.44
Subnet Mask . . . . . . . . . . : 255.255.255.0
Default Gateway . . . . . . . . : 192.168.10.1
DNS Servers . . . . . . . . . . : 0.0.0.0
```

**Expected response:**
```json
{
  "root_cause": "This PC's DNS server is set to 0.0.0.0, an invalid resolver address, likely due to a manual static override that is not being replaced by the DHCP-assigned DNS server.",
  "confidence": 55,
  "osi_layer": "Application (Layer 7)",
  "evidence": [
    "ipconfig output: 'DNS Servers . . . : 0.0.0.0', which is not a usable resolver"
  ],
  "next_command": "show ip dhcp binding | include 192.168.10.44",
  "fix_steps": [
    "Check whether this PC's network adapter is set to 'Obtain DNS server address automatically' or has a manual static DNS entry.",
    "If static, either correct it to the intended DNS server or switch it back to automatic/DHCP.",
    "Release and renew the DHCP lease (ipconfig /release then /renew) if switched to automatic.",
    "Re-test name resolution with nslookup after the change."
  ],
  "severity": "Low",
  "concept": "Invalid statically-configured DNS server on a single host",
  "needs_human_review": true
}
```

Note the confidence is only 55 because the evidence shows the symptom (an
invalid DNS entry) but not the root *cause* of why it is static instead of
DHCP-assigned — the model is transparent about that gap and requests the
DHCP binding table as the next command.
