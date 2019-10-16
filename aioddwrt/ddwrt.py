"""Module for ddwrt."""
import inspect
import logging
import math
import re
from collections import namedtuple
from datetime import datetime

from aioddwrt.connection import SshConnection, TelnetConnection, HttpConnection
from aioddwrt.helpers import convert_size

_LOGGER = logging.getLogger(__name__)

CHANGE_TIME_CACHE_DEFAULT = 5  # Default 60s

_LEASES_CMD = 'cat /tmp/dnsmasq.leases'
_LEASES_REGEX = re.compile(
    r'\w+\s' +
    r'(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))\s' +
    r'(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s' +
    r'(?P<host>([^\s]+))')

# Command to get both 5GHz and 2.4GHz clients
_WL_CMD = ('nvram show 2> /dev/null | grep \'wl._ifname\' | awk -F '
           '\'=\' \'{cmd="wl -i " $2 " assoclist"; while(cmd | '
           'getline var) print var}\' | awk \'{print $2}\'')
_IW_CMD = ('iw dev | grep Interface | awk \'{cmd="iw dev " $2 " station'
           ' dump"; while(cmd | getline var) print var}\' | grep Station'
           ' | awk \'{print $2}\'')
_MAC_REGEX = re.compile(r'(?P<mac>([0-9A-Fa-f]{1,2}\:){5}[0-9A-Fa-f]{1,2})')

_ARP_CMD = 'arp -n'
_ARP_REGEX = re.compile(
    r'.+\s' +
    r'\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s' +
    r'.+\s' +
    r'(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))' +
    r'\s' +
    r'.*')

_RX_COMMAND = 'cat /sys/class/net/eth0/statistics/rx_bytes'
_TX_COMMAND = 'cat /sys/class/net/eth0/statistics/tx_bytes'


_HTTP_DATA = re.compile(r'\{(\w+)::([^\}]*)\}')

Device = namedtuple('Device', ['mac', 'ip', 'name'])


class DdWrt:
    """This is the interface class."""

    def __init__(self, host=None, port=None, protocol='ssh', username=None,
                 password=None, ssh_key=None, mode='router', http_session=None,
                 time_cache=CHANGE_TIME_CACHE_DEFAULT):
        """Init function."""
        self.mode = mode
        self.protocol = protocol
        self._rx_latest = None
        self._tx_latest = None
        self._latest_transfer_check = None
        self._cache_time = time_cache
        self._trans_cache_timer = None
        self._transfer_rates_cache = None
        self._latest_transfer_data = 0, 0
        self._wl_cmd = None

        if protocol == 'http':
            self.connection = HttpConnection(host, http_session, username,
                                             password)
        elif protocol == 'telnet':
            self.connection = TelnetConnection(
                host, port, username, password)
        else:
            self.connection = SshConnection(
                host, port, username, password, ssh_key)

    async def async_set_wl_cmd(self):
        lines = await self.connection.async_run_command('wl ver')
        if lines and 'version' in lines[1]:
            wl_cmd = _WL_CMD
        else:
            wl_cmd = _IW_CMD
        return wl_cmd

    @staticmethod
    async def _parse_lines(lines, regex):
        """Parse the lines using the given regular expression.

        If a line can't be parsed it is logged and skipped in the output.
        """
        results = []
        if inspect.iscoroutinefunction(lines):
            lines = await lines
        for line in lines:
            if line:
                match = regex.search(line)
                if not match:
                    _LOGGER.debug("Could not parse row: %s", line)
                    continue
                results.append(match.groupdict())
        return results

    @staticmethod
    async def _parse_http_data(response):
        return {key: val for key, val in _HTTP_DATA.findall(response)}

    async def _parse_http_wl(self, response):
        """Parse wireless data returned by web."""
        data = await self._parse_http_data(response)
        active_wireless = data.get('active_wireless')
        if not active_wireless:
            return []

        # The DD-WRT UI uses its own data format and then
        # regex's out values so this is done here too
        # Remove leading and trailing single quotes.
        clean_str = active_wireless.strip().strip("'")
        elements = clean_str.split("','")

        return [item for item in elements if _MAC_REGEX.match(item)]

    async def _parse_http_leases(self, response):
        """Parse lease data returned by web."""
        # Remove leading and trailing quotes and spaces
        data = await self._parse_http_data(response)
        cleaned_str = data.get('dhcp_leases').replace(
            "\"", "").replace("\'", "").replace(" ", "")
        elements = cleaned_str.split(',')
        num_clients = int(len(elements) / 5)
        results = []
        for idx in range(0, num_clients):
            # The data is a single array
            # every 5 elements represents one host, the MAC
            # is the third element and the name is the first.
            mac_index = (idx * 5) + 2
            if mac_index < len(elements):
                results.append(
                    {'mac': elements[(idx * 5) + 2],
                     'ip': elements[(idx * 5) + 1],
                     'host': elements[idx * 5]})
        return results

    async def async_get_wl(self):
        if self.protocol == 'http':
            response = await self.connection.async_get_page(
                'Status_Wireless.live.asp')
            result = await self._parse_http_wl(response)
        else:
            if not self._wl_cmd:
                self._wl_cmd = await self.async_set_wl_cmd()
            lines = await self.connection.async_run_command(self._wl_cmd)
            if not lines:
                return []
            result = await self._parse_lines(lines, _MAC_REGEX)
        devices = []
        for device in result:
            devices.append(device['mac'].upper())
        return devices

    async def async_get_leases(self):
        if self.protocol == 'http':
            response = await self.connection.async_get_page(
                'Status_Lan.live.asp')
            result = await self._parse_http_leases(response)
        else:
            lines = await self.connection.async_run_command(_LEASES_CMD)
            if not lines:
                return {}
            lines = [line for line in lines if not line.startswith('duid ')]
            result = await self._parse_lines(lines, _LEASES_REGEX)
        devices = {}
        for device in result:
            # For leases where the client doesn't set a hostname, ensure it
            # is blank and not '*', which breaks entity_id down the line.
            if device['host'] == '*':
                device['host'] = ''
            device['mac'] = device['mac'].upper()
            devices[device['mac']] = device
        return devices

    async def async_get_arp(self):
        if self.protocol == 'http':
            return {}
        lines = await self.connection.async_run_command(_ARP_CMD)
        if not lines:
            return {}
        result = await self._parse_lines(lines, _ARP_REGEX)
        devices = {}
        for device in result:
            if device['mac'] is not None:
                mac = device['mac'].upper()
                devices[mac] = Device(mac, device['ip'], None)
        return devices

    async def async_get_bytes_total(self, use_cache=True):
        """Retrieve total bytes (rx an tx) from DDWRT."""
        now = datetime.utcnow()
        if use_cache and self._trans_cache_timer and self._cache_time > \
                (now - self._trans_cache_timer).total_seconds():
            return self._transfer_rates_cache

        rx = await self.async_get_rx()
        tx = await self.async_get_tx()
        return rx, tx

    async def async_get_rx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(_RX_COMMAND)
        return int(data[0])

    async def async_get_tx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(_TX_COMMAND)
        return int(data[0])

    async def async_get_current_transfer_rates(self, use_cache=True):
        """Gets current transfer rates calculated in per second in bytes."""
        now = datetime.utcnow()
        data = await self.async_get_bytes_total(use_cache)
        if self._rx_latest is None or self._tx_latest is None:
            self._latest_transfer_check = now
            self._rx_latest = data[0]
            self._tx_latest = data[1]
            return self._latest_transfer_data

        time_diff = now - self._latest_transfer_check
        if time_diff.total_seconds() < 30:
            return self._latest_transfer_data

        if data[0] < self._rx_latest:
            rx = data[0]
        else:
            rx = data[0] - self._rx_latest
        if data[1] < self._tx_latest:
            tx = data[1]
        else:
            tx = data[1] - self._tx_latest
        self._latest_transfer_check = now

        self._rx_latest = data[0]
        self._tx_latest = data[1]

        self._latest_transfer_data = (
            math.ceil(rx / time_diff.total_seconds()) if rx > 0 else 0,
            math.ceil(tx / time_diff.total_seconds()) if tx > 0 else 0)
        return self._latest_transfer_data

    async def async_current_transfer_human_readable(
            self, use_cache=True):
        """Gets current transfer rates in a human readable format."""
        rx, tx = await self.async_get_current_transfer_rates(use_cache)

        return "%s/s" % convert_size(rx), "%s/s" % convert_size(tx)

    @property
    def is_connected(self):
        return self.connection.is_connected

    async def clean_up(self):
        await self.connection.clean_up()
