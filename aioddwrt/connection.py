"""Module for connections."""
import asyncio
import logging
from asyncio import LimitOverrunError, TimeoutError

import asyncssh
import aiohttp

_LOGGER = logging.getLogger(__name__)

asyncssh.set_log_level('WARNING')


class SshConnection:
    """Maintains an SSH connection to an DD-WRT router."""

    def __init__(self, host, port, username, password, ssh_key):
        """Initialize the SSH connection properties."""

        self._connected = False
        self._host = host
        self._port = port or 22
        self._username = username
        self._password = password
        self._ssh_key = ssh_key
        self._client = None

    async def async_run_command(self, command, retry=False):
        """Run commands through an SSH connection.

        Connect to the SSH server if not currently connected, otherwise
        use the existing connection.
        """
        if not self.is_connected:
            await self.async_connect()
        _LOGGER.debug('Running "{}" at {}'.format(command, self._host))
        try:
            result = await asyncio.wait_for(self._client.run(command), 9)
        except asyncssh.misc.ChannelOpenError:
            if not retry:
                await self.async_connect()
                return self.async_run_command(command, retry=True)
            else:
                self._connected = False
                _LOGGER.error("No connection to host")
                return []
        except TimeoutError:
            del self._client
            self._connected = False
            _LOGGER.error("Host timeout.")
            return []
        _LOGGER.debug('Command "{}" returned {} at {}'.format(
            command, str(result), self._host))
        self._connected = True
        return result.stdout.split('\n')

    @property
    def is_connected(self):
        """Do we have a connection."""
        return self._connected

    async def async_connect(self):
        """Fetches the client or creates a new one."""

        kwargs = {
            'username': self._username if self._username else None,
            'client_keys': [self._ssh_key] if self._ssh_key else None,
            'port': self._port,
            'password': self._password if self._password else None,
            'known_hosts': None
        }

        _LOGGER.debug('Connecting to {} with kwargs {}'.format(
            self._host, str(kwargs)))

        self._client = await asyncssh.connect(self._host, **kwargs)
        self._connected = True

    async def clean_up(self):
        pass


class TelnetConnection:
    """Maintains a Telnet connection to an DD-WRT router."""

    def __init__(self, host, port, username, password):
        """Initialize the Telnet connection properties."""

        self._reader = None
        self._writer = None
        self._host = host
        self._port = port or 23
        self._username = username
        self._password = password
        self._prompt_string = None
        self._connected = False
        self._io_lock = asyncio.Lock()

    async def async_run_command(self, command, first_try=True):
        """Run a command through a Telnet connection.
        Connect to the Telnet server if not currently connected, otherwise
        use the existing connection.
        """
        await self.async_connect()
        _LOGGER.debug('Running "{}" at {}'.format(command, self._host))
        try:
            with (await self._io_lock):
                self._writer.write('{}\n'.format(command).encode('ascii'))
                data = ((await asyncio.wait_for(self._reader.readuntil(
                    self._prompt_string), 9)).split(b'\n')[1:-1])

        except (BrokenPipeError, LimitOverrunError):
            if first_try:
                return await self.async_run_command(command, False)
            else:
                _LOGGER.warning("connection is lost to host.")
                return[]
        except TimeoutError:
            _LOGGER.error("Host timeout.")
            return []
        finally:
            self._writer.close()

        _LOGGER.debug('Command "{}" returned {} at {}'.format(
            command, str(data), self._host))

        return [line.decode('utf-8') for line in data]

    async def async_connect(self):
        """Connect to the DD-WRT Telnet server."""
        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port)

        with (await self._io_lock):
            try:
                await asyncio.wait_for(self._reader.readuntil(b'login: '), 9)
            except asyncio.streams.IncompleteReadError:
                _LOGGER.error(
                    "Unable to read from router on %s:%s" % (
                        self._host, self._port))
                return
            except TimeoutError:
                _LOGGER.error("Host timeout.")
            self._writer.write((self._username + '\n').encode('ascii'))
            await self._reader.readuntil(b'Password: ')

            self._writer.write((self._password + '\n').encode('ascii'))

            self._prompt_string = (await self._reader.readuntil(
                b'#')).split(b'\n')[-1]
        self._connected = True

    @property
    def is_connected(self):
        """Do we have a connection."""
        return self._connected

    async def disconnect(self):
        """Disconnects the client"""
        self._writer.close()

    async def clean_up(self):
        await self.disconnect()


class HttpConnection(object):

    def __init__(self, hostname, username, password):
        self.host = hostname
        self.username = username
        self.password = password
        self.session = None
        # mark as connected
        self.is_connected = True

    async def async_set_session(self):
        if not self.session:
            msg = "Creating HTTP session with login: {} and password {}"
            _LOGGER.debug(msg.format(self.username, self.password))
            self.session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(login=self.username,
                                       password=self.password))

    async def async_get_page(self, page, retry=False):
        _LOGGER.debug("Getting {}".format(page))
        if not self.session:
            await self.async_set_session()
        url = "http://{}/{}".format(self.host, page)
        async with self.session.get(url) as response:
            msg = "Status {} for {}"
            _LOGGER.debug(msg.format(response.status, url))
            data = await response.text()
            msg = "Response {} for {}"
            _LOGGER.debug(msg.format(url, data))
            return data

    async def clean_up(self):
        if self.session:
            await self.session.close()
