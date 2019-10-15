import asyncio
import pytest
from aioddwrt.ddwrt import (DdWrt, _LEASES_CMD, _WL_CMD, _ARP_CMD,
                            Device, _RX_COMMAND, _TX_COMMAND)

RX_DATA = ["2703926881", ""]
TX_DATA = ["648110137", ""]

RX = 2703926881
TX = 648110137

WL_DATA = [
    '01:02:03:04:06:08\r',
    '08:09:10:11:12:14\r',
    '08:09:10:11:12:15\r',
    'AB:CD:DE:AB:CD:EF\r'
]

WL_DEVICES = [
    '01:02:03:04:06:08',
    '08:09:10:11:12:14',
    '08:09:10:11:12:15',
    'AB:CD:DE:AB:CD:EF',
]

ARP_DATA = [
    '? (123.123.123.125) at 01:02:03:04:06:08 [ether]  on eth0\r',
    '? (123.123.123.126) at 08:09:10:11:12:14 [ether]  on br0\r',
    '? (123.123.123.128) at AB:CD:DE:AB:CD:EF [ether]  on br0\r',
    '? (123.123.123.127) at <incomplete>  on br0\r',
    '? (172.16.10.2) at 00:25:90:12:2D:90 [ether]  on br0\r',
]

ARP_DEVICES = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip='123.123.123.128', name=None),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}

LEASES_DATA = [
    '51910 01:02:03:04:06:08 123.123.123.125 TV 01:02:03:04:06:08\r',
    '79986 01:02:03:04:06:10 123.123.123.127 android 01:02:03:04:06:15\r',
    '23523 08:09:10:11:12:14 123.123.123.126 * 08:09:10:11:12:14\r',
]

LEASES_DEVICES = {
    '01:02:03:04:06:08': {
        'mac': '01:02:03:04:06:08', 'ip': '123.123.123.125', 'host': 'TV'},
    '08:09:10:11:12:14': {
        'mac': '08:09:10:11:12:14', 'ip': '123.123.123.126', 'host': ''},
    '01:02:03:04:06:10': {
        'mac': '01:02:03:04:06:10', 'ip': '123.123.123.127',
        'host': 'android'},
}

WAKE_DEVICES = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name='TV'),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=''),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}

WAKE_DEVICES_AP = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip='123.123.123.128', name=None),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}

WAKE_DEVICES_NO_IP = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=None),
    '08:09:10:11:12:15': Device(
        mac='08:09:10:11:12:15', ip=None, name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip='123.123.123.128', name=None),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}

HTTP_LAN_DATA = """
{lan_mac::AA:BB:CC:DD:EE:F0}
{lan_ip::192.168.1.1}
{lan_ip_prefix::192.168.1.}
{lan_netmask::255.255.255.0}
{lan_gateway::0.0.0.0}
{lan_dns::8.8.8.8}
{lan_proto::dhcp}
{dhcp_daemon::DNSMasq}
{dhcp_start::100}
{dhcp_num::50}
{dhcp_lease_time::1440}
{dhcp_leases:: 'TV','123.123.123.125','01:02:03:04:06:08','1 day 00:00:00','113','android','123.123.123.127','01:02:03:04:06:10','Static','201','*','123.123.123.126','08:09:10:11:12:14','Static','201'}}
{pptp_leases::}
{pppoe_leases::}
{arp_table:: 'device_1','192.168.1.113','AA:BB:CC:DD:EE:00','13','device_2','192.168.1.201','AA:BB:CC:DD:EE:01','1'}
{uptime:: 12:28:48 up 132 days, 18:02,  load average: 0.15, 0.19, 0.21}
{ipinfo::&nbsp;IP: 192.168.0.108}
"""

HTTP_WL_DATA = """
{wl_mac::AA:BB:CC:DD:EE:FF}
{wl_ssid::WIFI_SSD}
{wl_channel::10}
{wl_radio::Radio is On}
{wl_xmit::Auto}
{wl_rate::72 Mbps}
{wl_ack::}
{active_wireless::'AA:BB:CC:DD:EE:00','eth1','3:13:14','72M','24M','HT20','-9','-92','83','1048','AA:BB:CC:DD:EE:01','eth1','10:48:22','72M','72M','HT20','-40','-92','52','664'}
{active_wds::}
{packet_info::SWRXgoodPacket=173673555;SWRXerrorPacket=27;SWTXgoodPacket=311344396;SWTXerrorPacket=3107;}
{uptime:: 12:29:23 up 132 days, 18:03,  load average: 0.16, 0.19, 0.20}
{ipinfo::&nbsp;IP: 192.168.0.108}
"""


def HttpPageMock(page, *args, **kwargs):
    f = asyncio.Future()
    if page == "Status_Lan.live.asp":
        f.set_result(HTTP_LAN_DATA)
        return f
    if page == "Status_Wireless.live.asp":
        f.set_result(HTTP_WL_DATA)
        return f


def RunCommandMock(command, *args, **kwargs):
    f = asyncio.Future()
    if command == _WL_CMD:
        f.set_result(WL_DATA)
        return f
    if command == _LEASES_CMD:
        f.set_result(LEASES_DATA)
        return f
    if command == _ARP_CMD:
        f.set_result(ARP_DATA)
        return f
    if command == _RX_COMMAND:
        f.set_result(RX_DATA)
        return f
    if command == _TX_COMMAND:
        f.set_result(TX_DATA)
        return f
    if command == 'wl ver':
        f.set_result(['wl ver', 'version x.x.x'])
        return f
    raise Exception("Unhandled command: %s" % command)


def RunCommandEmptyMock(command, *args, **kwargs):
    f = asyncio.Future()
    f.set_result("")
    return f


@pytest.mark.asyncio
async def test_get_wl(event_loop, mocker):
    """Testing wl."""
    mocker.patch(
        'aioddwrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = DdWrt(host="localhost", port=22)
    devices = await scanner.async_get_wl()
    assert WL_DEVICES == devices


@pytest.mark.asyncio
async def test_get_wl_empty(event_loop, mocker):
    """Testing wl."""
    mocker.patch(
        'aioddwrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandEmptyMock)
    scanner = DdWrt(host="localhost", port=22)
    devices = await scanner.async_get_wl()
    assert [] == devices


@pytest.mark.asyncio
async def test_async_get_leases(event_loop, mocker):
    """Testing leases."""
    mocker.patch(
        'aioddwrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = DdWrt(host="localhost", port=22)
    data = await scanner.async_get_leases()
    assert LEASES_DEVICES == data


@pytest.mark.asyncio
async def test_async_get_http_leases(event_loop, mocker):
    mocker.patch(
        'aioddwrt.connection.HttpConnection.async_get_page',
        side_effect=HttpPageMock)
    scanner = DdWrt(host="localhost", protocol='http', port=22)
    data = await scanner.async_get_leases()
    assert LEASES_DEVICES == data


@pytest.mark.asyncio
async def test_get_arp(event_loop, mocker):
    """Testing arp."""
    mocker.patch(
        'aioddwrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = DdWrt(host="localhost", port=22)
    data = await scanner.async_get_arp()
    assert ARP_DEVICES == data


@pytest.mark.asyncio
async def test_get_packets_total(event_loop, mocker):
    """Test getting packet totals."""
    mocker.patch(
        'aioddwrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = DdWrt(host="localhost", port=22, mode='ap', require_ip=False)
    data = await scanner.async_get_tx()
    assert TX == data
    data = await scanner.async_get_rx()
    assert RX == data

