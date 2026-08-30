"""
tools_generate_data.py
-----------------------
One-off generator used to build data/cases.csv and data/sample_cases.json.
It is NOT part of the runtime application (main.py / dashboard.py never
import this file) — it exists purely so the dataset's origin is
transparent and reproducible for the viva.

Each case is built from a small template per fault category so that the
"symptom", "topology_note", "show_outputs" and "expected_fault" are always
mutually consistent (e.g. if a case claims "administratively down", the
show ip interface brief output for that interface really does say
"administratively down").

Run:  python3 tools_generate_data.py
"""
import json
import csv
import os

CASES = []


def add_case(case_id, symptom, topology_note, show_outputs, expected_fault,
             osi_layer, concept, severity):
    CASES.append({
        "case_id": case_id,
        "symptom": symptom,
        "topology_note": topology_note,
        "show_outputs": show_outputs,
        "expected_fault": expected_fault,
        "osi_layer": osi_layer,
        "concept": concept,
        "severity": severity,
    })


def block(cmd, text):
    return f"{cmd}\n{text.strip()}"


# ---------------------------------------------------------------------------
# 1. VLAN cases (6)
# ---------------------------------------------------------------------------
add_case(
    "CASE-001",
    "PC-A (VLAN 10, Sales) cannot ping PC-B (VLAN 10, Sales) even though both "
    "are on the same access switch SW1.",
    "SW1 Fa0/1 -> PC-A, SW1 Fa0/2 -> PC-B. Both ports are intended to be "
    "access ports for VLAN 10, but Fa0/2 may be incorrectly assigned to another VLAN. Verify the interface VLAN configuration.",
    {
        "show vlan brief": (
            "VLAN Name                             Status    Ports\n"
            "---- -------------------------------- --------- -------------------------------\n"
            "1    default                          active    Fa0/3, Fa0/4\n"
            "10   Sales                             active    Fa0/1\n"
            "20   Engineering                       active    Fa0/5, Fa0/6"
        ),
        "show running-config": (
            "interface FastEthernet0/1\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            "!\n"
            "interface FastEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 20"
        ),
    },
    "Fa0/2 was configured for VLAN 20 instead of VLAN 10, so PC-A and PC-B "
    "are on different broadcast domains.",
    "Layer 2 (Data Link)",
    "VLAN membership / access port misconfiguration",
    "Medium",
)

add_case(
    "CASE-002",
    "All hosts on VLAN 30 (Server farm) lost connectivity to VLAN 10 and "
    "VLAN 20 at the same time, but hosts within VLAN 30 can still reach "
    "each other.",
    "SW1 Gi0/1 is the trunk link to the distribution switch SW-DIST. SW1 "
    "hosts VLAN 10, 20 and 30 access ports.",
    {
        "show interfaces trunk": (
            "Port        Mode         Encapsulation  Status        Native vlan\n"
            "Gi0/1       auto         n-802.1q       trunking      1\n\n"
            "Port        Vlans allowed on trunk\n"
            "Gi0/1       10,20"
        ),
        "show vlan brief": (
            "VLAN Name                             Status    Ports\n"
            "---- -------------------------------- --------- -------------------------------\n"
            "10   Sales                             active    Fa0/1\n"
            "20   Engineering                       active    Fa0/5\n"
            "30   Servers                            active    Fa0/10"
        ),
    },
    "VLAN 30 is missing from the allowed VLAN list on trunk Gi0/1, so its "
    "traffic is being pruned at the trunk instead of forwarded upstream.",
    "Layer 2 (Data Link)",
    "Trunk allowed-VLAN misconfiguration",
    "High",
)

add_case(
    "CASE-003",
    "A newly added PC on Fa0/8 gets no VLAN connectivity at all and cannot "
    "obtain an IP address.",
    "Fa0/8 was patched in today for a temporary contractor laptop.",
    {
        "show vlan brief": (
            "VLAN Name                             Status    Ports\n"
            "---- -------------------------------- --------- -------------------------------\n"
            "1    default                          active    Fa0/2, Fa0/3, Fa0/4\n"
            "10   Sales                             active    Fa0/1\n"
            "40   Guest                              active    (no ports assigned)"
        ),
        "show running-config": (
            "interface FastEthernet0/8\n"
            " switchport mode access\n"
            " switchport access vlan 40"
        ),
    },
    "Fa0/8 is assigned to VLAN 40, but VLAN 40 does not exist in the VLAN "
    "database, so the port cannot forward traffic for that VLAN.",
    "Layer 2 (Data Link)",
    "Missing / undefined VLAN",
    "Medium",
)

add_case(
    "CASE-004",
    "Two switches SW1 and SW2 are directly connected, but hosts in VLAN 10 "
    "on SW2 cannot reach VLAN 10 hosts on SW1.",
    "SW1 Gi0/2 <-> SW2 Gi0/1 is meant to be an 802.1q trunk carrying VLAN 10 "
    "and VLAN 20.",
    {
        "show interfaces trunk": (
            "-- no interfaces are currently in trunking mode --"
        ),
        "show running-config": (
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 10"
        ),
    },
    "Gi0/2 on SW1 was left as an access port for VLAN 10 instead of being "
    "configured as a trunk, so VLAN 20 traffic between the switches is "
    "dropped and VLAN 10 depends entirely on native/access behaviour.",
    "Layer 2 (Data Link)",
    "Trunk not formed (access port used for inter-switch link)",
    "High",
)

add_case(
    "CASE-005",
    "PC-C in VLAN 10 can reach the default gateway but cannot reach PC-D, "
    "also in VLAN 10 on the same switch.",
    "SW1 Fa0/1 -> PC-C, SW1 Fa0/4 -> PC-D. Both configured as access ports "
    "for VLAN 10.",
    {
        "show vlan brief": (
            "VLAN Name                             Status    Ports\n"
            "---- -------------------------------- --------- -------------------------------\n"
            "10   Sales                             active    Fa0/1, Fa0/4"
        ),
        "show interfaces status": (
            "Port      Name               Status       Vlan       Duplex  Speed\n"
            "Fa0/1     PC-C               connected    10         a-full  a-100\n"
            "Fa0/4     PC-D               err-disabled 10         a-full  a-100"
        ),
    },
    "Fa0/4 has been placed into err-disabled state (likely by port "
    "security or a storm-control violation), so PC-D is physically "
    "isolated from the VLAN even though its configuration looks correct.",
    "Layer 1/2 (Physical / Data Link)",
    "Err-disabled port",
    "Medium",
)

add_case(
    "CASE-006",
    "An internal web server is unreachable from the Internet on its public "
    "IP (203.0.113.10), even though internal clients can reach the server "
    "fine on its private address and NAT shows active translations for "
    "other traffic.",
    "R1 uses a static NAT entry to publish the web server: public "
    "203.0.113.10 maps to the server's internal address. The server was "
    "rebuilt on new hardware two weeks ago.",
    {
        "show running-config (nat)": (
            "ip nat inside source static 192.168.10.20 203.0.113.10\n"
            "!\n"
            "interface GigabitEthernet0/0.10\n"
            " ip address 192.168.10.1 255.255.255.0\n"
            " ip nat inside\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " ip address 203.0.113.5 255.255.255.252\n"
            " ip nat outside"
        ),
        "show ip dhcp binding": (
            "IP address       Client-ID/Hardware address    Lease expiration        Type\n"
            "192.168.10.30    0100.5079.6845.ab             Infinite                 Manual"
        ),
        "change record note": (
            "2026-08-10: WEBSVR1 rebuilt on new hardware, re-IP'd to 192.168.10.30 "
            "(previously 192.168.10.20). DNS and internal firewall rules were "
            "updated; NAT was not."
        ),
    },
    "The static NAT entry still maps public 203.0.113.10 to the server's "
    "old internal address (192.168.10.20). The server was re-IP'd to "
    "192.168.10.30 during a rebuild, so inbound translated traffic is now "
    "sent to an address nothing is listening on.",
    "Layer 3 (Network)",
    "Static NAT entry pointing to a stale internal IP after a server change",
    "High",
)



# ---------------------------------------------------------------------------
# 2. Default gateway cases (4)
# ---------------------------------------------------------------------------
add_case(
    "CASE-007",
    "PC-E (192.168.10.15/24) can ping other hosts on its own subnet but "
    "cannot reach anything outside VLAN 10, including the router.",
    "PC-E is on VLAN 10, gateway should be R1's sub-interface 192.168.10.1.",
    {
        "PC-E ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.10.15\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.0\n"
            "Default Gateway . . . . . . . . : 192.168.10.254"
        ),
        "show ip interface brief (R1)": (
            "Interface              IP-Address      OK? Method Status                Protocol\n"
            "GigabitEthernet0/0.10  192.168.10.1    YES manual up                    up"
        ),
    },
    "PC-E's configured default gateway (192.168.10.254) does not match the "
    "router's actual sub-interface address (192.168.10.1), so off-subnet "
    "traffic has nowhere to go.",
    "Layer 3 (Network)",
    "Default gateway mismatch",
    "High",
)

add_case(
    "CASE-008",
    "All PCs on VLAN 20 lost access to every other network at the same "
    "time; local VLAN 20 communication still works.",
    "R1 sub-interface Gi0/0.20 is the gateway for VLAN 20 (192.168.20.1/24).",
    {
        "show ip interface brief (R1)": (
            "Interface              IP-Address      OK? Method Status                    Protocol\n"
            "GigabitEthernet0/0.20  192.168.20.1    YES manual administratively down     down"
        ),
    },
    "Sub-interface Gi0/0.20 is administratively down, so the gateway for "
    "VLAN 20 is completely unreachable even though the IP address itself "
    "is configured correctly.",
    "Layer 1/3 (Physical / Network)",
    "Gateway interface administratively down",
    "Critical",
)

add_case(
    "CASE-009",
    "A single PC (192.168.30.22) cannot reach the gateway while every other "
    "PC on the same VLAN can.",
    "VLAN 30 subnet is 192.168.30.0/24, gateway 192.168.30.1.",
    {
        "PC ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.30.22\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.128\n"
            "Default Gateway . . . . . . . . : 192.168.30.1"
        ),
    },
    "This PC's subnet mask (255.255.255.128 / /25) does not match the rest "
    "of VLAN 30 (/24), placing it in a different calculated subnet than the "
    "gateway even though the gateway IP is typed correctly.",
    "Layer 3 (Network)",
    "Incorrect subnet mask",
    "Medium",
)

add_case(
    "CASE-010",
    "Branch office PCs can reach their local gateway and local servers but "
    "cannot reach the HQ subnet 10.10.0.0/16.",
    "Branch router R2 connects to HQ over a serial WAN link that is up.",
    {
        "show ip route (R2)": (
            "Gateway of last resort is not set\n\n"
            "     172.16.0.0/24 is subnetted, 1 subnets\n"
            "C       172.16.5.0 is directly connected, Serial0/0/0\n"
            "     192.168.40.0/24 is subnetted, 1 subnets\n"
            "C       192.168.40.0 is directly connected, GigabitEthernet0/0"
        ),
    },
    "There is no route to 10.10.0.0/16 (static or via a routing protocol) "
    "in R2's routing table, so the branch simply does not know how to reach "
    "HQ even though the physical WAN link is up.",
    "Layer 3 (Network)",
    "Missing route to remote network",
    "High",
)

# ---------------------------------------------------------------------------
# 3. DHCP cases (5)
# ---------------------------------------------------------------------------
add_case(
    "CASE-011",
    "A newly connected PC in VLAN 10 receives a 169.254.x.x address instead "
    "of an address from the expected 192.168.10.0/24 pool.",
    "R1 is configured as the DHCP server for VLAN 10 using an ip helper-"
    "address is not required since R1 is directly attached.",
    {
        "show running-config (R1)": (
            "ip dhcp pool VLAN10\n"
            " network 192.168.10.0 255.255.255.0\n"
            " default-router 192.168.10.1\n"
            " dns-server 8.8.8.8\n"
            "!\n"
            "interface GigabitEthernet0/0.10\n"
            " encapsulation dot1Q 10\n"
            " ip address 192.168.10.1 255.255.255.0\n"
            " shutdown"
        ),
    },
    "The DHCPDISCOVER never reaches the server because sub-interface "
    "Gi0/0.10 is administratively shut down, so the PC times out and "
    "self-assigns an APIPA address.",
    "Layer 1/3 (Physical / Network)",
    "DHCP unreachable due to shutdown gateway interface",
    "High",
)

add_case(
    "CASE-012",
    "Most PCs in VLAN 20 get an IP address normally, but the last few PCs "
    "that boot up each morning fail to get a lease.",
    "VLAN 20 has roughly 40 hosts that all power on around the same time.",
    {
        "show ip dhcp pool VLAN20": (
            "Pool VLAN20 :\n"
            " Network: 192.168.20.0 mask 255.255.255.0\n"
            " Leased addresses       : 30\n"
            " Excluded addresses     : 5   (192.168.20.1 - 192.168.20.5)\n"
            " Total addresses        : 30\n"
            " Pending event          : none"
        ),
    },
    "The pool only has 30 usable addresses (254 minus exclusions minus a "
    "pool sized too small for the subnet), and all 30 are already leased, "
    "so late-booting hosts cannot obtain an address — this is pool "
    "exhaustion, not a reachability problem.",
    "Layer 3 (Network) / Application (DHCP service)",
    "DHCP pool exhaustion",
    "Medium",
)

add_case(
    "CASE-013",
    "PCs in VLAN 30 receive an IP address, subnet mask and gateway, but the "
    "gateway address handed out is on a completely different subnet than "
    "the PCs themselves.",
    "VLAN 30 subnet is 192.168.30.0/24.",
    {
        "show running-config (R1)": (
            "ip dhcp pool VLAN30\n"
            " network 192.168.30.0 255.255.255.0\n"
            " default-router 192.168.31.1\n"
            " dns-server 8.8.8.8"
        ),
    },
    "The DHCP pool's default-router (192.168.31.1) is outside the "
    "192.168.30.0/24 network it serves, so clients receive an unreachable "
    "gateway even though they get a valid IP/mask.",
    "Layer 3 (Network) / Application (DHCP service)",
    "Incorrect DHCP default-router / network mismatch",
    "High",
)

add_case(
    "CASE-014",
    "No PC in the newly created VLAN 60 (Warehouse) can obtain an IP "
    "address; every device shows an APIPA address.",
    "VLAN 60 was added to the switch and router sub-interface this week.",
    {
        "show running-config (R1)": (
            "interface GigabitEthernet0/0.60\n"
            " encapsulation dot1Q 60\n"
            " ip address 192.168.60.1 255.255.255.0\n"
            "!\n"
            "ip dhcp pool VLAN10\n"
            " network 192.168.10.0 255.255.255.0\n"
            " default-router 192.168.10.1"
        ),
    },
    "There is no DHCP pool defined for the 192.168.60.0/24 network at all "
    "(only VLAN10's pool exists), so VLAN 60 clients have no server to "
    "answer their requests.",
    "Application (DHCP service)",
    "Missing DHCP pool for new VLAN",
    "High",
)

add_case(
    "CASE-015",
    "A PC that used to work fine now shows an IP address that conflicts "
    "with an existing server, and both devices report intermittent "
    "connectivity.",
    "Server-SVR1 has a static IP of 192.168.10.50. PC-F is DHCP-assigned.",
    {
        "PC-F ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.10.50\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.0"
        ),
        "show ip dhcp pool VLAN10": (
            "Pool VLAN10 :\n"
            " Network: 192.168.10.0 mask 255.255.255.0\n"
            " Excluded addresses     : none configured"
        ),
    },
    "192.168.10.50 was never excluded from the DHCP pool even though it is "
    "statically assigned to SVR1, so DHCP eventually leased that same "
    "address to PC-F, creating a duplicate IP conflict.",
    "Layer 3 (Network)",
    "Duplicate IP address (missing DHCP exclusion)",
    "Critical",
)

# ---------------------------------------------------------------------------
# 4. DNS cases (4)
# ---------------------------------------------------------------------------
add_case(
    "CASE-016",
    "PCs can ping 8.8.8.8 successfully but cannot open any website by "
    "name, and 'ping www.google.com' fails with 'Ping request could not "
    "find host'.",
    "PCs receive DNS server address via DHCP from R1.",
    {
        "show running-config (R1)": (
            "ip dhcp pool VLAN10\n"
            " network 192.168.10.0 255.255.255.0\n"
            " default-router 192.168.10.1\n"
            " dns-server 192.168.10.1"
        ),
        "PC nslookup": (
            "*** 192.168.10.1 can't find www.google.com: Server failed"
        ),
    },
    "The DHCP pool hands out the router's own interface (192.168.10.1) as "
    "the DNS server, but R1 is not actually configured as a DNS "
    "server/forwarder, so name resolution fails even though basic IP "
    "connectivity is fine.",
    "Application (Layer 7)",
    "Invalid / non-functional DNS server address",
    "Medium",
)

add_case(
    "CASE-017",
    "One department (VLAN 20) cannot resolve internal hostnames like "
    "'fileserver.corp.local', while VLAN 10 resolves the same name fine.",
    "Both VLANs are supposed to use the internal DNS server at "
    "10.10.10.53.",
    {
        "show running-config (R1)": (
            "ip dhcp pool VLAN10\n"
            " dns-server 10.10.10.53\n"
            "!\n"
            "ip dhcp pool VLAN20\n"
            " dns-server 8.8.8.8"
        ),
    },
    "VLAN 20's DHCP pool points clients to a public DNS server (8.8.8.8) "
    "instead of the internal DNS server (10.10.10.53), so it cannot resolve "
    "internal-only hostnames.",
    "Application (Layer 7)",
    "Wrong DNS server for internal name resolution",
    "Low",
)

add_case(
    "CASE-018",
    "Every device across the whole network suddenly cannot resolve any "
    "hostname, but IP connectivity to every internal and external address "
    "still works.",
    "10.10.10.53 is the sole internal DNS server used by all VLANs.",
    {
        "ping 10.10.10.53": (
            "Request timed out.\nRequest timed out.\nRequest timed out.\n"
            "Request timed out.\n\nPacket Loss = 100%"
        ),
        "show ip interface brief (DNS-SVR)": (
            "Interface       IP-Address      OK? Method Status                Protocol\n"
            "FastEthernet0   10.10.10.53     YES manual administratively down down"
        ),
    },
    "The DNS server's own network interface has been administratively "
    "shut down, taking the single point of failure DNS service offline for "
    "the entire network while routing between other hosts is unaffected.",
    "Application (Layer 7) / Layer 1 (Physical)",
    "DNS server unreachable (interface down)",
    "Critical",
)

add_case(
    "CASE-019",
    "A specific PC cannot resolve any hostname while every other PC on the "
    "same VLAN resolves names normally.",
    "All PCs on VLAN 10 are DHCP clients of R1.",
    {
        "PC ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.10.44\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.0\n"
            "Default Gateway . . . . . . . . : 192.168.10.1\n"
            "DNS Servers . . . . . . . . . . : 0.0.0.0"
        ),
    },
    "This PC was manually configured with a static DNS server of 0.0.0.0 "
    "(overriding DHCP), which is not a valid resolver address, unlike the "
    "rest of the VLAN which uses the DHCP-assigned DNS server.",
    "Application (Layer 7)",
    "Invalid statically-configured DNS server on a single host",
    "Low",
)

# ---------------------------------------------------------------------------
# 5. Routing cases (5)
# ---------------------------------------------------------------------------
add_case(
    "CASE-020",
    "R1 (HQ) and R2 (Branch) are connected over a serial link that shows "
    "'up/up', but PCs behind R2 cannot reach PCs behind R1.",
    "Both routers run OSPF area 0 on all links.",
    {
        "show ip route (R1)": (
            "Gateway of last resort is not set\n\n"
            "C    192.168.10.0/24 is directly connected, GigabitEthernet0/0.10\n"
            "C    172.16.5.0/30 is directly connected, Serial0/0/0"
        ),
        "show ip protocols (R1)": (
            "Routing Protocol is \"ospf 1\"\n"
            "  Routing for Networks:\n"
            "    192.168.10.0 0.0.0.255 area 0\n"
            "  (172.16.5.0/30 is not advertised into OSPF)"
        ),
    },
    "The serial transit network 172.16.5.0/30 was never added to an OSPF "
    "network statement on R1, so OSPF never forms/advertises correctly "
    "across the link and R2's networks never appear in R1's routing table.",
    "Layer 3 (Network)",
    "Missing OSPF network statement",
    "High",
)

add_case(
    "CASE-021",
    "PCs behind R2 can reach R1's directly connected networks, but cannot "
    "reach a newly added server subnet 192.168.99.0/24 behind R1.",
    "192.168.99.0/24 was added to R1 today for a new server VLAN.",
    {
        "show ip route (R2)": (
            "C    172.16.5.0/30 is directly connected, Serial0/0/0\n"
            "O    192.168.10.0/24 [110/65] via 172.16.5.1, Serial0/0/0\n"
            "     -- no entry for 192.168.99.0/24 --"
        ),
        "show run | section router ospf (R1)": (
            "router ospf 1\n"
            " network 192.168.10.0 0.0.0.255 area 0\n"
            " network 172.16.5.0 0.0.0.3 area 0"
        ),
    },
    "192.168.99.0/24 was never added to R1's OSPF network statements, so "
    "OSPF is not advertising the new server subnet to R2 even though the "
    "interface itself is up.",
    "Layer 3 (Network)",
    "New subnet not redistributed/advertised into routing protocol",
    "Medium",
)

add_case(
    "CASE-022",
    "A static default route was configured, but the branch router still "
    "cannot reach the Internet even though its ISP-facing interface is up.",
    "R2 Gi0/1 connects to the ISP router at 203.0.113.1.",
    {
        "show ip route (R2)": (
            "S*   0.0.0.0/0 [1/0] via 203.0.113.254\n"
            "C    203.0.113.0/30 is directly connected, GigabitEthernet0/1"
        ),
    },
    "The static default route points to next-hop 203.0.113.254, which is "
    "outside the 203.0.113.0/30 directly connected subnet, so the next hop "
    "is unreachable and the default route can never be used.",
    "Layer 3 (Network)",
    "Static route with unreachable next hop",
    "High",
)

add_case(
    "CASE-023",
    "Two networks that used to route fine now show intermittent packet "
    "loss, and traceroute shows packets bouncing between R1 and R3.",
    "R1 and R3 both have static routes to 192.168.50.0/24 pointing at each "
    "other.",
    {
        "show ip route (R1)": "S    192.168.50.0/24 [1/0] via 172.16.1.2 (R3)",
        "show ip route (R3)": "S    192.168.50.0/24 [1/0] via 172.16.1.1 (R1)",
    },
    "Both R1 and R3 have a static route for 192.168.50.0/24 pointing at "
    "each other instead of at the actual subnet owner, creating a routing "
    "loop that produces the observed intermittent loss.",
    "Layer 3 (Network)",
    "Routing loop from misconfigured static routes",
    "High",
)

add_case(
    "CASE-024",
    "After a firmware update, R1 no longer forwards any traffic between "
    "VLAN 10 and VLAN 20, even though both sub-interfaces show up/up.",
    "R1 previously routed between VLAN 10 (192.168.10.0/24) and VLAN 20 "
    "(192.168.20.0/24) using router-on-a-stick.",
    {
        "show ip interface brief (R1)": (
            "Interface              IP-Address      OK? Method Status  Protocol\n"
            "GigabitEthernet0/0     unassigned      YES unset  up      up\n"
            "GigabitEthernet0/0.10  192.168.10.1    YES manual up      up\n"
            "GigabitEthernet0/0.20  192.168.20.1    YES manual up      up"
        ),
        "show ip route (R1)": "-- routing table is empty --",
    },
    "The routing table is completely empty even though both sub-interfaces "
    "are up — the running-config confirms 'no ip routing' was applied "
    "during the firmware update, disabling Layer 3 forwarding on the "
    "router entirely.",
    "Layer 3 (Network)",
    "IP routing disabled on router",
    "Critical",
)

# ---------------------------------------------------------------------------
# 6. ACL cases (4)
# ---------------------------------------------------------------------------
add_case(
    "CASE-025",
    "PC gets an IP address and can ping its gateway, but cannot reach the "
    "file server SVR1 (192.168.30.50) in VLAN 30, while other VLANs can.",
    "VLAN 30 hosts the server subnet, protected by an inbound ACL on R1's "
    "Gi0/0.30 sub-interface.",
    {
        "show access-lists": (
            "Extended IP access list SERVER_ACL\n"
            "    10 permit tcp 192.168.20.0 0.0.0.255 host 192.168.30.50 eq 80\n"
            "    20 deny ip 192.168.10.0 0.0.0.255 host 192.168.30.50\n"
            "    30 permit ip any any"
        ),
        "show running-config (R1, interface)": (
            "interface GigabitEthernet0/0.30\n"
            " ip access-group SERVER_ACL in"
        ),
    },
    "ACL entry 20 explicitly denies all traffic from the 192.168.10.0/24 "
    "(VLAN 10) subnet to SVR1, while VLAN 20 is only permitted for HTTP — "
    "the reporting PC is on VLAN 10 and is being blocked by this explicit "
    "deny statement.",
    "Layer 3/4 (Network/Transport)",
    "ACL explicit deny blocking legitimate traffic",
    "High",
)

add_case(
    "CASE-026",
    "Remote management via SSH to R1 stopped working from the admin "
    "subnet, but SSH still works from every other subnet.",
    "192.168.99.0/24 is the dedicated admin/management subnet.",
    {
        "show access-lists": (
            "Standard IP access list VTY_ACCESS\n"
            "    10 deny   192.168.99.0 0.0.0.255\n"
            "    20 permit any"
        ),
        "show running-config (line vty)": (
            "line vty 0 4\n"
            " access-class VTY_ACCESS in\n"
            " transport input ssh"
        ),
    },
    "The VTY access-class explicitly denies the admin subnet "
    "(192.168.99.0/24) before the permit-any statement, so ironically the "
    "one subnet that should manage the router is blocked from doing so.",
    "Layer 3/4 (Network/Transport) / Application (SSH)",
    "ACL misconfiguration on VTY lines",
    "High",
)

add_case(
    "CASE-027",
    "Web traffic from VLAN 10 to the Internet works, but FTP to an "
    "internal FTP server in VLAN 30 fails only for VLAN 10.",
    "FTP_ACL is applied on R1 Gi0/0.30 sub-interface protecting the FTP "
    "server 192.168.30.60.",
    {
        "show access-lists": (
            "Extended IP access list FTP_ACL\n"
            "    10 permit tcp any host 192.168.30.60 eq 80"
        ),
    },
    "FTP_ACL only permits TCP port 80 (HTTP) to the server, but never "
    "explicitly permits TCP ports 20/21 (FTP), and there is no trailing "
    "'permit ip any any' — the implicit deny at the end of the ACL is "
    "blocking FTP traffic.",
    "Layer 4 (Transport)",
    "ACL missing required port permit (implicit deny)",
    "Medium",
)

add_case(
    "CASE-028",
    "NAT is configured and the ISP link is up, but internal PCs still "
    "cannot browse the Internet — 'show ip nat translations' shows no "
    "active translations.",
    "R1 performs PAT (NAT overload) for 192.168.10.0/24 going out "
    "Gi0/1 (ISP).",
    {
        "show access-lists": (
            "Standard IP access list NAT_SRC\n"
            "    10 deny   192.168.10.0 0.0.0.255"
        ),
        "show running-config (nat)": (
            "ip nat inside source list NAT_SRC interface GigabitEthernet0/1 overload"
        ),
    },
    "The ACL that defines which traffic NAT should translate (NAT_SRC) "
    "explicitly denies the 192.168.10.0/24 subnet, so NAT never matches "
    "and translates any of that subnet's traffic, even though NAT itself "
    "is enabled correctly.",
    "Layer 3/4 (Network/Transport)",
    "ACL used by NAT denies the source traffic it should permit",
    "High",
)

# ---------------------------------------------------------------------------
# 7. NAT cases (3, in addition to CASE-028 above which is ACL+NAT)
# ---------------------------------------------------------------------------
add_case(
    "CASE-029",
    "PCs in VLAN 10 can ping R1's inside interface but cannot reach any "
    "Internet address; 'show ip nat translations' is completely empty.",
    "R1 Gi0/0.10 is the inside interface, Gi0/1 connects to the ISP.",
    {
        "show running-config (nat)": (
            "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
            "!\n"
            "interface GigabitEthernet0/0.10\n"
            " ip address 192.168.10.1 255.255.255.0\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " ip address 203.0.113.5 255.255.255.252\n"
            "access-list 1 permit 192.168.10.0 0.0.0.255"
        ),
    },
    "Neither Gi0/0.10 nor Gi0/1 has been marked with 'ip nat inside' / "
    "'ip nat outside', so even though the 'ip nat inside source' statement "
    "and ACL are correct, NAT never actually triggers on any interface.",
    "Layer 3 (Network)",
    "Missing ip nat inside/outside interface marking",
    "High",
)

add_case(
    "CASE-030",
    "Internet access worked yesterday but has stopped for all internal "
    "PCs today; 'show ip nat statistics' shows the translation count is "
    "stuck at the same number and not increasing.",
    "R1 uses PAT overload out Gi0/1 to the ISP.",
    {
        "show ip nat statistics": (
            "Total active translations: 0 (0 static, 0 dynamic; 0 extended)\n"
            "Outside interfaces:\n"
            "  Serial0/0/1\n"
            "Inside interfaces:\n"
            "  GigabitEthernet0/0.10"
        ),
    },
    "The outside interface is listed as Serial0/0/1, but the actual "
    "ISP-facing interface in this topology is GigabitEthernet0/1 — 'ip nat "
    "outside' was applied to the wrong (unused) interface, so translations "
    "never occur.",
    "Layer 3 (Network)",
    "ip nat outside applied to the wrong interface",
    "High",
)

add_case(
    "CASE-031",
    "Internal PCs can reach some Internet sites but time out on others; "
    "'show ip nat translations' shows entries that stop updating after a "
    "few minutes of heavy use.",
    "R1 performs PAT overload using its single public IP for the whole "
    "192.168.0.0/16 internal supernet.",
    {
        "show ip nat statistics": (
            "Total active translations: 4092 (0 static, 4092 dynamic; 4092 extended)\n"
            "Hits: 88210  Misses: 512\n"
            "Expired translations: 3"
        ),
    },
    "The single overload address has run out of available source ports "
    "(NAT port pool exhaustion) under heavy load from a /16 of internal "
    "hosts sharing one public IP, causing new sessions to intermittently "
    "fail while established ones continue to work.",
    "Layer 4 (Transport)",
    "NAT overload port exhaustion",
    "Medium",
)

# ---------------------------------------------------------------------------
# 8. Wireless cases (4)
# ---------------------------------------------------------------------------
add_case(
    "CASE-032",
    "A laptop shows the corporate SSID 'CORP-WIFI' in its available "
    "network list but fails to associate, staying stuck at 'Connecting...'.",
    "AP1 broadcasts CORP-WIFI using WPA2-PSK.",
    {
        "show running-config (AP1)": (
            "dot11 ssid CORP-WIFI\n"
            " authentication open\n"
            " authentication key-management wpa version 2\n"
            " wpa-psk ascii 0 CorpSecret2024"
        ),
    },
    "The SSID mixes 'authentication open' with WPA2-PSK key management — "
    "this inconsistent security configuration causes clients configured "
    "for standard WPA2-Personal to fail the 4-way handshake and never "
    "fully associate.",
    "Layer 2 (Data Link)",
    "Inconsistent wireless security configuration",
    "Medium",
)

add_case(
    "CASE-033",
    "All wireless clients on AP2 associate successfully and show 'Connected "
    "no internet' with a self-assigned 169.254.x.x address.",
    "AP2 is configured as a bridge/access point onto VLAN 10, where R1's "
    "DHCP pool for VLAN 10 lives.",
    {
        "show running-config (AP2)": (
            "interface Dot11Radio0\n"
            " bridge-group 1\n"
            "!\n"
            "interface GigabitEthernet0\n"
            " bridge-group 2"
        ),
    },
    "The wireless radio interface is in bridge-group 1 while the wired "
    "uplink interface is in bridge-group 2 — the two are never bridged "
    "together, so wireless clients are isolated from the wired network and "
    "its DHCP server.",
    "Layer 2 (Data Link)",
    "Bridge-group mismatch isolating wireless from wired network",
    "High",
)

add_case(
    "CASE-034",
    "Wireless clients near AP3 experience frequent disconnects and very "
    "slow speeds, while clients near AP4 (same building) are fine.",
    "AP3 and AP4 are both 2.4 GHz APs roughly 20 metres apart.",
    {
        "show controllers Dot11Radio0 (AP3)": "Channel: 6",
        "show controllers Dot11Radio0 (AP4)": "Channel: 6",
    },
    "AP3 and AP4 are both operating on the same 2.4 GHz channel (6) with "
    "overlapping coverage, causing co-channel interference that degrades "
    "performance for clients near AP3, which sits closer to the overlap "
    "zone.",
    "Layer 1 (Physical)",
    "Co-channel wireless interference",
    "Low",
)

add_case(
    "CASE-035",
    "A visitor's device cannot see or connect to the 'GUEST-WIFI' SSID at "
    "all, even standing directly next to the access point.",
    "AP5 is supposed to broadcast both CORP-WIFI and GUEST-WIFI.",
    {
        "show running-config (AP5)": (
            "dot11 ssid CORP-WIFI\n"
            " vlan 10\n"
            " authentication open\n"
            "!\n"
            "dot11 ssid GUEST-WIFI\n"
            " vlan 40\n"
            " authentication open\n"
            " guest-mode disabled"
        ),
    },
    "GUEST-WIFI has 'guest-mode disabled', which means the SSID is "
    "configured but not being broadcast (it is a closed/hidden network), "
    "so it never appears in the visitor's scan list.",
    "Layer 1/2 (Physical / Data Link)",
    "SSID broadcast disabled (guest-mode not enabled)",
    "Low",
)

# ---------------------------------------------------------------------------
# Canonical category assignment
# ---------------------------------------------------------------------------
# Each case gets exactly ONE explicit category, chosen for its true root
# cause (not just words that happen to appear in the symptom text). This
# replaces the earlier approach of inferring category by fuzzy keyword
# matching against symptom/concept text, which double- and mis-counted
# cases whose symptom mentions e.g. "VLAN 20" even when the root cause is
# actually a gateway or DHCP fault. See docs/architecture.md for rationale.
#
# Target distribution (per project audit):
#   VLAN 5, Gateway 4, DHCP 5, DNS 4, Routing 5, ACL 4, NAT 4, Wireless 4
CATEGORY_MAP = {
    "CASE-001": "vlan", "CASE-002": "vlan", "CASE-003": "vlan",
    "CASE-004": "vlan", "CASE-005": "vlan",
    "CASE-007": "gateway", "CASE-008": "gateway", "CASE-009": "gateway",
    "CASE-010": "gateway",
    "CASE-011": "dhcp", "CASE-012": "dhcp", "CASE-013": "dhcp",
    "CASE-014": "dhcp", "CASE-015": "dhcp",
    "CASE-016": "dns", "CASE-017": "dns", "CASE-018": "dns", "CASE-019": "dns",
    "CASE-020": "routing", "CASE-021": "routing", "CASE-022": "routing",
    "CASE-023": "routing", "CASE-024": "routing",
    "CASE-025": "acl", "CASE-026": "acl", "CASE-027": "acl", "CASE-028": "acl",
    "CASE-006": "nat", "CASE-029": "nat", "CASE-030": "nat", "CASE-031": "nat",
    "CASE-032": "wireless", "CASE-033": "wireless", "CASE-034": "wireless",
    "CASE-035": "wireless",
}

for case in CASES:
    if case["case_id"] not in CATEGORY_MAP:
        raise ValueError(f"{case['case_id']} has no category assigned in CATEGORY_MAP")
    case["category"] = CATEGORY_MAP[case["case_id"]]

_missing_ids = set(CATEGORY_MAP) - set(c["case_id"] for c in CASES)
if _missing_ids:
    raise ValueError(f"CATEGORY_MAP references case_ids not in CASES: {_missing_ids}")

# ---------------------------------------------------------------------------
# Write out
# ---------------------------------------------------------------------------
os.makedirs("data", exist_ok=True)

with open("data/sample_cases.json", "w", encoding="utf-8") as f:
    json.dump(CASES, f, indent=2)

with open("data/cases.csv", "w", newline="", encoding="utf-8") as f:
    fieldnames = ["case_id", "symptom", "topology_note", "show_outputs",
                  "expected_fault", "osi_layer", "concept", "severity", "category"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for c in CASES:
        row = dict(c)
        row["show_outputs"] = json.dumps(c["show_outputs"])
        writer.writerow(row)

print(f"Generated {len(CASES)} cases -> data/cases.csv and data/sample_cases.json")

from collections import Counter  # noqa: E402
print("Category distribution:", dict(Counter(c["category"] for c in CASES)))
