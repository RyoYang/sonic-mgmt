import logging
import pytest

from tests.common.helpers.assertions import pytest_assert
from tests.generic_config_updater.gu_utils import apply_patch, expect_op_success, expect_op_failure
from tests.generic_config_updater.gu_utils import generate_tmpfile, delete_tmpfile
from tests.generic_config_updater.gu_utils import create_checkpoint, delete_checkpoint, rollback_or_reload
from tests.generic_config_updater.gu_utils import create_path, check_show_ip_intf, check_vrf_route_for_intf

# Test on t0 topo to verify functionality and to choose predefined variable
# "LOOPBACK_INTERFACE": {
#     "Loopback0": {},
#     "Loopback0|10.1.0.32/32": {},
#     "Loopback0|FC00:1::32/128": {}
# }
# admin@vlab-01:~$ show ip interfaces | grep Loopback0
# Loopback0                  10.1.0.32/32         up/up         N/A             N/A
# admin@vlab-01:~$ show ipv6 interfaces | grep Loopback0
# Loopback0                         fc00:1::32/128                              up/up         N/A             N/A
#                                   fe80::4a3:18ff:fec2:f9e3%Loopback0/64                     N/A             N/A

pytestmark = [
    pytest.mark.topology('t0'),
]

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def setup_env(duthosts, rand_one_dut_hostname):
    """
    Setup/teardown fixture for each loopback interface test.
    rollback to check if it goes back to starting config without vrf set

    Args:
        duthosts: list of DUTs.
        rand_selected_dut: The fixture returns a randomly selected DuT.
    """
    duthost = duthosts[rand_one_dut_hostname]
    create_checkpoint(duthost)

    yield

    try:
        logger.info("Rolled back to original checkpoint")
        rollback_or_reload(duthost)
        check_show_ip_intf(duthost, "Loopback0", ["10.1.0.32/32"],
                           ["Vrf"], is_ipv4=True)
        check_show_ip_intf(duthost, "Loopback0", ["fc00:1::32/128"],
                           ["Vrf"], is_ipv4=False)
    finally:
        delete_checkpoint(duthost)


def cleanup_lo_interface_config(duthost, cfg_facts):
    lo_interfaces = cfg_facts.get('LOOPBACK_INTERFACE', {})
    for lo_interface in lo_interfaces:
        del_loopback_interface = duthost.shell(
            "sudo config loopback del {}".format(lo_interface),
            module_ignore_errors=True)
        pytest_assert(
            not del_loopback_interface['rc'],
            "Loopback interface '{}' is not deleted successfully".format(lo_interface)
        )

def lo_interface_tc1_add_init(duthost):
    """ test initial addition of v4 and v6 lo intf

    Expected output
    "LOOPBACK_INTERFACE": {
        "Loopback0": {},
        "Loopback0|10.1.0.32/32": {},
        "Loopback0|FC00:1::32/128": {}
    }
    """
    json_patch = [
        {
            "op": "add",
            "path": "/LOOPBACK_INTERFACE",
            "value": {
                "Loopback0": {},
                "Loopback0|10.1.0.32/32": {},
                "Loopback0|FC00:1::32/128": {}
            }
        }
    ]

    tmpfile = generate_tmpfile(duthost)
    logger.info("tmpfile {}".format(tmpfile))

    try:
        output = apply_patch(duthost, json_data=json_patch, dest_file=tmpfile)
        expect_op_success(duthost, output)

        check_show_ip_intf(duthost, "Loopback0", ["10.1.0.32/32"],
                           [], is_ipv4=True)
        check_show_ip_intf(duthost, "Loopback0", ["fc00:1::32/128"],
                           [], is_ipv4=False)

    finally:
        delete_tmpfile(duthost, tmpfile)


def lo_interface_tc1_add_duplicate(duthost):
    """ Add v4 and v6 duplicate lo intf to config

    Initial Loopback setup in t0
    "LOOPBACK_INTERFACE": {
        "Loopback0": {},
        "Loopback0|10.1.0.32/32": {},
        "Loopback0|FC00:1::32/128": {}
    }
    """
    json_patch = [
        {
            "op": "add",
            "path": create_path(["LOOPBACK_INTERFACE",
                                "Loopback0|10.1.0.32/32"]),
            "value": {}
        },
        {
            "op": "add",
            "path": create_path(["LOOPBACK_INTERFACE",
                                "Loopback0|FC00:1::32/128"]),
            "value": {}
        }
    ]

    tmpfile = generate_tmpfile(duthost)
    logger.info("tmpfile {}".format(tmpfile))

    try:
        output = apply_patch(duthost, json_data=json_patch, dest_file=tmpfile)
        expect_op_success(duthost, output)

        check_show_ip_intf(duthost, "Loopback0", ["10.1.0.32/32"],
                           [], is_ipv4=True)
        check_show_ip_intf(duthost, "Loopback0", ["fc00:1::32/128"],
                           [], is_ipv4=False)
    finally:
        delete_tmpfile(duthost, tmpfile)


def lo_interface_tc1_xfail(duthost):
    """ Test expect fail testcase

    ("add", "Loopback0", "587.1.0.32~132", "FC00:1::32~1128"), ADD Invalid IPv4 address
    ("add", "Loopback0", "10.1.0.32~132", "FC00:1::xyz~1128"), ADD Invalid IPv6 address
    ("remove", "Loopback0", "10.1.0.33~132", "FC00:1::32~1128"), REMOVE Unexist IPv4 address
    ("remove", "Loopback0", "10.1.0.32~132", "FC00:1::33~1128") REMOVE Unexist IPv6 address
    """
    xfail_input = [
        ("add", "Loopback0", "587.1.0.32/32", "FC00:1::32/128"),
        ("add", "Loopback0", "10.1.0.32/32", "FC00:1::xyz/128"),
        ("remove", "Loopback0", "10.1.0.33/32", "FC00:1::32/128"),
        ("remove", "Loopback0", "10.1.0.32/32", "FC00:1::33/128")
    ]
    for op, name, dummy_lo_interface_v4, dummy_lo_interface_v6 in xfail_input:
        dummy_lo_interface_v4 = name + "|" + dummy_lo_interface_v4
        dummy_lo_interface_v6 = name + "|" + dummy_lo_interface_v6
        json_patch = [
            {
                "op": "{}".format(op),
                "path": create_path(["LOOPBACK_INTERFACE",
                                    dummy_lo_interface_v4]),
                "value": {}
            },
            {
                "op": "{}".format(op),
                "path": create_path(["LOOPBACK_INTERFACE",
                                    dummy_lo_interface_v6]),
                "value": {}
            }
        ]

        tmpfile = generate_tmpfile(duthost)
        logger.info("tmpfile {}".format(tmpfile))

        try:
            output = apply_patch(duthost, json_data=json_patch, dest_file=tmpfile)
            expect_op_failure(output)
        finally:
            delete_tmpfile(duthost, tmpfile)


def lo_interface_tc1_replace(duthost):
    """ Replace v4 and v6 loopback intf ip
    Expected output
    "LOOPBACK_INTERFACE": {
        "Loopback0": {},
        "Loopback0|10.1.0.33/32": {},
        "Loopback0|FC00:1::33/128": {}
    }
    admin@vlab-01:~$ show ip interfaces | grep Loopback0
    Loopback0                  10.1.0.33/32         up/up         N/A             N/A
    admin@vlab-01:~$ show ipv6 interfaces | grep Loopback0
    Loopback0                         fc00:1::33/128                              up/up         N/A             N/A
                                      fe80::a8cb:e8ff:fe6e:df6e%Loopback0/64                    N/A             N/A
    """
    json_patch = [
        {
            "op": "remove",
            "path": create_path(["LOOPBACK_INTERFACE",
                                "Loopback0|10.1.0.32/32"])
        },
        {
            "op": "remove",
            "path": create_path(["LOOPBACK_INTERFACE",
                                "Loopback0|FC00:1::32/128"])
        },
        {
            "op": "add",
            "path": create_path(["LOOPBACK_INTERFACE",
                                "Loopback0|10.1.0.33/32"]),
            "value": {}
        },
        {
            "op": "add",
            "path": create_path(["LOOPBACK_INTERFACE",
                                "Loopback0|FC00:1::33/128"]),
            "value": {}
        }
    ]

    tmpfile = generate_tmpfile(duthost)
    logger.info("tmpfile {}".format(tmpfile))

    try:
        output = apply_patch(duthost, json_data=json_patch, dest_file=tmpfile)
        expect_op_success(duthost, output)

        check_show_ip_intf(duthost, "Loopback0", ["10.1.0.33/32"],
                           ["10.1.0.32/32"], is_ipv4=True)
        check_show_ip_intf(duthost, "Loopback0", ["fc00:1::33/128"],
                           ["fc00:1::32/128"], is_ipv4=False)
    finally:
        delete_tmpfile(duthost, tmpfile)


def lo_interface_tc1_remove(duthost):
    """ Remove v4 and v6 loopback intf config
    """
    json_patch = [
        {
            "op": "remove",
            "path": "/LOOPBACK_INTERFACE"
        }
    ]

    tmpfile = generate_tmpfile(duthost)
    logger.info("tmpfile {}".format(tmpfile))

    try:
        output = apply_patch(duthost, json_data=json_patch, dest_file=tmpfile)
        expect_op_success(duthost, output)

        check_show_ip_intf(duthost, "Loopback0", [],
                           ["10.1.0.33/32"], is_ipv4=True)
        check_show_ip_intf(duthost, "Loopback0", [],
                           ["fc00:1::33/128"], is_ipv4=False)
    finally:
        delete_tmpfile(duthost, tmpfile)


def setup_vrf_config(duthost):
    """Create two vrf and bind Loopback0 to Vrf_01

    admin@vlab-01:~$ show ip interfaces | grep Loopback0
    Loopback0        Vrf_01    10.1.0.32/32         up/up         N/A             N/A
    admin@vlab-01:~$ show ipv6 interfaces | grep Loopback0
    Loopback0        Vrf_01           fc00:1::32/128                              up/up         N/A             N/A
                                      fe80::a8cb:e8ff:fe6e:df6e%Loopback0/64                    N/A             N/A
    admin@vlab-01:~$ show ip route vrf Vrf_01
    VRF Vrf_01:
    C>* 10.1.0.32/32 is directly connected, Loopback0, 00:00:13

    """
    cmds = []
    cmds.append("config vrf add Vrf_01")
    cmds.append("config vrf add Vrf_02")

    output = duthost.shell_cmds(cmds=cmds)

    json_patch = [
        {
            "op": "add",
            "path": "/LOOPBACK_INTERFACE/Loopback0/vrf_name",
            "value": "Vrf_01"
        }
    ]

    tmpfile = generate_tmpfile(duthost)
    logger.info("tmpfile {}".format(tmpfile))

    try:
        output = apply_patch(duthost, json_data=json_patch, dest_file=tmpfile)
        expect_op_success(duthost, output)

        check_show_ip_intf(duthost, "Loopback0", ["10.1.0.32/32", "Vrf_01"], [], is_ipv4=True)
        check_show_ip_intf(duthost, "Loopback0", ["fc00:1::32/128", "Vrf_01"], [], is_ipv4=False)

        check_vrf_route_for_intf(duthost, "Vrf_01", "Loopback0", is_ipv4=True)
        check_vrf_route_for_intf(duthost, "Vrf_01", "Loopback0", is_ipv4=False)
    finally:
        delete_tmpfile(duthost, tmpfile)


def test_lo_interface_tc1_suite(rand_selected_dut, cfg_facts):
    cleanup_lo_interface_config(rand_selected_dut, cfg_facts)
    lo_interface_tc1_add_init(rand_selected_dut)
    lo_interface_tc1_add_duplicate(rand_selected_dut)
    lo_interface_tc1_xfail(rand_selected_dut)
    lo_interface_tc1_replace(rand_selected_dut)
    lo_interface_tc1_remove(rand_selected_dut)


def test_lo_interface_tc2_vrf_change(rand_selected_dut):
    """ Replace lo interface vrf

    admin@vlab-01:~$ show ip interfaces | grep Loopback0
    Loopback0        Vrf_02    10.1.0.32/32         up/up         N/A             N/A
    admin@vlab-01:~$ show ipv6 interfaces | grep Loopback0
    Loopback0        Vrf_02           fc00:1::32/128                              up/up         N/A             N/A
                                      fe80::a8cb:e8ff:fe6e:df6e%Loopback0/64                    N/A             N/A
    admin@vlab-01:~$ show ip route vrf Vrf_02
    VRF Vrf_02:
    C>* 10.1.0.32/32 is directly connected, Loopback0, 00:00:17
    """
    setup_vrf_config(rand_selected_dut)
    json_patch = [
        {
            "op": "replace",
            "path": "/LOOPBACK_INTERFACE/Loopback0/vrf_name",
            "value": "Vrf_02"
        }
    ]

    tmpfile = generate_tmpfile(rand_selected_dut)
    logger.info("tmpfile {}".format(tmpfile))

    try:
        output = apply_patch(rand_selected_dut, json_data=json_patch, dest_file=tmpfile)
        expect_op_success(rand_selected_dut, output)

        check_show_ip_intf(rand_selected_dut, "Loopback0", ["10.1.0.32/32", "Vrf_02"],
                           [], is_ipv4=True)
        check_show_ip_intf(rand_selected_dut, "Loopback0", ["fc00:1::32/128", "Vrf_02"],
                           [], is_ipv4=False)

        check_vrf_route_for_intf(rand_selected_dut, "Vrf_02", "Loopback0", is_ipv4=True)
        check_vrf_route_for_intf(rand_selected_dut, "Vrf_02", "Loopback0", is_ipv4=False)
    finally:
        delete_tmpfile(rand_selected_dut, tmpfile)
