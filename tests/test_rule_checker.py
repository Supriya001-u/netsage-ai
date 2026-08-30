"""
tests/test_rule_checker.py
----------------------------
Unit tests for the deterministic (non-AI) rule checker.

Run with:
    python3 -m pytest tests/ -v
or, without pytest installed:
    python3 tests/test_rule_checker.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rule_checker import (  # noqa: E402
    check_acl_blocking,
    check_duplicate_ip,
    check_gateway_mismatch,
    check_incorrect_dhcp_network,
    check_interface_down,
    check_missing_dhcp_pool,
    check_missing_route,
    check_missing_vlan,
    check_nat_missing,
    check_nat_translation_absent,
    check_trunk_mismatch,
    check_wrong_subnet_mask,
)


def test_wrong_subnet_mask_detected():
    show_outputs = {
        "PC-A ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.30.10\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.0"
        ),
        "PC-B ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.30.22\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.128"
        ),
    }
    result = check_wrong_subnet_mask(show_outputs)
    assert result["status"] == "FAIL"


def test_wrong_subnet_mask_pass_when_consistent():
    show_outputs = {
        "PC-A ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.30.10\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.0"
        ),
        "PC-B ipconfig": (
            "IPv4 Address. . . . . . . . . . : 192.168.30.22\n"
            "Subnet Mask . . . . . . . . . . : 255.255.255.0"
        ),
    }
    result = check_wrong_subnet_mask(show_outputs)
    assert result["status"] == "PASS"


def test_missing_route_detected():
    show_outputs = {
        "show ip route (R2)": (
            "C    172.16.5.0/30 is directly connected, Serial0/0/0\n"
            "O    192.168.10.0/24 [110/65] via 172.16.5.1, Serial0/0/0\n"
            "     -- no entry for 192.168.99.0/24 --"
        ),
    }
    result = check_missing_route(show_outputs)
    assert result["status"] == "FAIL"


def test_missing_route_pass_when_populated():
    show_outputs = {
        "show ip route (R2)": (
            "C    172.16.5.0/30 is directly connected, Serial0/0/0\n"
            "O    192.168.10.0/24 [110/65] via 172.16.5.1, Serial0/0/0\n"
            "O    192.168.99.0/24 [110/65] via 172.16.5.1, Serial0/0/0"
        ),
    }
    result = check_missing_route(show_outputs)
    assert result["status"] == "PASS"


def test_trunk_mismatch_vlan_pruned():
    show_outputs = {
        "show interfaces trunk": (
            "Port        Mode         Encapsulation  Status        Native vlan\n"
            "Gi0/1       auto         n-802.1q       trunking      1\n\n"
            "Port        Vlans allowed on trunk\n"
            "Gi0/1       10,20"
        ),
        "show vlan brief": (
            "VLAN Name       Status    Ports\n"
            "10   Sales       active    Fa0/1\n"
            "20   Eng         active    Fa0/5\n"
            "30   Servers     active    Fa0/10"
        ),
    }
    result = check_trunk_mismatch(show_outputs)
    assert result["status"] == "FAIL"
    assert "30" in result["evidence"]


def test_trunk_mismatch_pass_when_all_vlans_allowed():
    show_outputs = {
        "show interfaces trunk": (
            "Port        Mode         Encapsulation  Status        Native vlan\n"
            "Gi0/1       auto         n-802.1q       trunking      1\n\n"
            "Port        Vlans allowed on trunk\n"
            "Gi0/1       10,20,30"
        ),
        "show vlan brief": (
            "VLAN Name       Status    Ports\n"
            "10   Sales       active    Fa0/1\n"
            "20   Eng         active    Fa0/5\n"
            "30   Servers     active    Fa0/10"
        ),
    }
    result = check_trunk_mismatch(show_outputs)
    assert result["status"] == "PASS"


def test_trunk_not_formed_detected():
    show_outputs = {
        "show interfaces trunk": "-- no interfaces are currently in trunking mode --",
    }
    result = check_trunk_mismatch(show_outputs)
    assert result["status"] == "FAIL"


def test_acl_blocking_explicit_deny_detected():
    show_outputs = {
        "show access-lists": (
            "Extended IP access list SERVER_ACL\n"
            "    10 permit tcp 192.168.20.0 0.0.0.255 host 192.168.30.50 eq 80\n"
            "    20 deny ip 192.168.10.0 0.0.0.255 host 192.168.30.50"
        ),
    }
    result = check_acl_blocking(show_outputs)
    assert result["status"] == "WARN"


def test_acl_blocking_pass_when_permit_any_present():
    show_outputs = {
        "show access-lists": (
            "Extended IP access list OPEN_ACL\n"
            "    10 permit ip any any"
        ),
    }
    result = check_acl_blocking(show_outputs)
    assert result["status"] == "PASS"


def test_acl_blocking_standard_acl_no_false_positive():
    """Regression test: a standard/NAT-source ACL with only permit lines and
    no 'permit ip any any' should NOT be flagged — that convention only
    applies to extended ACLs. This was a false positive found during audit."""
    show_outputs = {
        "show running-config (nat)": (
            "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
            "access-list 1 permit 192.168.10.0 0.0.0.255"
        ),
    }
    result = check_acl_blocking(show_outputs)
    assert result["status"] == "PASS"


def test_duplicate_ip_detected():
    show_outputs = {
        "PC-A ipconfig": "IPv4 Address. . . . . . . . . . : 192.168.10.50",
        "PC-B ipconfig": "IPv4 Address. . . . . . . . . . : 192.168.10.50",
    }
    result = check_duplicate_ip(show_outputs)
    assert result["status"] == "FAIL"
    assert "192.168.10.50" in result["evidence"]


def test_duplicate_ip_not_falsely_flagged():
    show_outputs = {
        "PC-A ipconfig": "IPv4 Address. . . . . . . . . . : 192.168.10.50",
        "PC-B ipconfig": "IPv4 Address. . . . . . . . . . : 192.168.10.51",
    }
    result = check_duplicate_ip(show_outputs)
    assert result["status"] == "PASS"


def test_gateway_mismatch_detected():
    show_outputs = {
        "PC ipconfig": "Default Gateway . . . . . . . . : 192.168.10.254",
        "show ip interface brief (R1)": (
            "Interface  IP-Address    OK? Method Status Protocol\n"
            "Gi0/0.10   192.168.10.1  YES manual up     up"
        ),
    }
    result = check_gateway_mismatch(show_outputs)
    assert result["status"] == "FAIL"


def test_gateway_mismatch_pass_when_matching():
    show_outputs = {
        "PC ipconfig": "Default Gateway . . . . . . . . : 192.168.10.1",
        "show ip interface brief (R1)": (
            "Interface  IP-Address    OK? Method Status Protocol\n"
            "Gi0/0.10   192.168.10.1  YES manual up     up"
        ),
    }
    result = check_gateway_mismatch(show_outputs)
    assert result["status"] == "PASS"


def test_interface_administratively_down():
    show_outputs = {
        "show ip interface brief (R1)": (
            "Interface  IP-Address    OK? Method Status                    Protocol\n"
            "Gi0/0.20   192.168.20.1  YES manual administratively down     down"
        ),
    }
    result = check_interface_down(show_outputs)
    assert result["status"] == "FAIL"
    assert result["severity"] == "Critical"


def test_interface_up_does_not_false_positive():
    show_outputs = {
        "show ip interface brief (R1)": (
            "Interface  IP-Address    OK? Method Status Protocol\n"
            "Gi0/0.20   192.168.20.1  YES manual up     up"
        ),
    }
    result = check_interface_down(show_outputs)
    assert result["status"] == "PASS"


def test_missing_vlan_detected():
    show_outputs = {
        "show vlan brief": (
            "VLAN Name       Status    Ports\n"
            "10   Sales       active    Fa0/1"
        ),
        "show running-config": (
            "interface FastEthernet0/8\n"
            " switchport access vlan 40"
        ),
    }
    result = check_missing_vlan(show_outputs)
    assert result["status"] == "FAIL"
    assert "40" in result["evidence"]


def test_missing_vlan_pass_when_present():
    show_outputs = {
        "show vlan brief": (
            "VLAN Name       Status    Ports\n"
            "10   Sales       active    Fa0/1"
        ),
        "show running-config": (
            "interface FastEthernet0/1\n"
            " switchport access vlan 10"
        ),
    }
    result = check_missing_vlan(show_outputs)
    assert result["status"] == "PASS"


def test_missing_dhcp_pool_detected():
    show_outputs = {
        "show running-config (R1)": (
            "interface GigabitEthernet0/0.60\n"
            " ip address 192.168.60.1 255.255.255.0\n"
            "!\n"
            "ip dhcp pool VLAN10\n"
            " network 192.168.10.0 255.255.255.0\n"
            " default-router 192.168.10.1"
        ),
    }
    result = check_missing_dhcp_pool(show_outputs)
    assert result["status"] == "FAIL"
    assert "192.168.60" in result["evidence"]


def test_incorrect_dhcp_network_detected():
    show_outputs = {
        "show running-config (R1)": (
            "ip dhcp pool VLAN30\n"
            " network 192.168.30.0 255.255.255.0\n"
            " default-router 192.168.31.1"
        ),
    }
    result = check_incorrect_dhcp_network(show_outputs)
    assert result["status"] == "FAIL"


def test_incorrect_dhcp_network_pass_when_correct():
    show_outputs = {
        "show running-config (R1)": (
            "ip dhcp pool VLAN30\n"
            " network 192.168.30.0 255.255.255.0\n"
            " default-router 192.168.30.1"
        ),
    }
    result = check_incorrect_dhcp_network(show_outputs)
    assert result["status"] == "PASS"


def test_nat_missing_interface_marking():
    show_outputs = {
        "show running-config (nat)": (
            "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
            "access-list 1 permit 192.168.10.0 0.0.0.255"
        ),
    }
    result = check_nat_missing(show_outputs)
    assert result["status"] == "FAIL"


def test_nat_translation_absent_detected():
    show_outputs = {
        "show ip nat statistics": "Total active translations: 0 (0 static, 0 dynamic; 0 extended)",
    }
    result = check_nat_translation_absent(show_outputs)
    assert result["status"] == "FAIL"


def test_nat_translation_present_passes():
    show_outputs = {
        "show ip nat statistics": "Total active translations: 12 (0 static, 12 dynamic; 12 extended)",
    }
    result = check_nat_translation_absent(show_outputs)
    assert result["status"] == "PASS"


def _run_all_tests_manually():
    """Fallback runner for environments without pytest installed."""
    test_fns = [obj for name, obj in globals().items()
                if name.startswith("test_") and callable(obj)]
    passed, failed = 0, 0
    for fn in test_fns:
        try:
            fn()
            print(f"PASS: {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {fn.__name__} -> {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    _run_all_tests_manually()
