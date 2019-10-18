Async API for [DD-WRT] devices. 

This has been forked from [aioasuswrt] and adapted for [DD-WRT]

[DD-WRT]: https://dd-wrt.com
[aioasuswrt]: https://github.com/kennedyshead/aioasuswrt

## Credits:
[@kennedyshead](https://github.com/kennedyshead)

## Info
There are many different versions of [DD-WRT] and sometimes they just don't work 
in current implementation.
If you have a problem with your specific router open an issue, but please add 
as much info as you can and at least:

* Version of router
* Version of [DD-WRT]

### How to run tests

`python setup.py test`

## Known issues

## Bugs
You can always create an issue in this tracker.
To test and give us the information needed you could run:
```python
#!/usr/bin/env python
import asyncio
import logging

import sys

from aioddwrt.ddwrt import DdWrt

component = DdWrt('192.168.1.1', 22, username='****', password='****')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def print_data():
    logger.debug("wl")
    logger.debug(await component.connection.async_run_command(
        'for dev in `nvram get wl_ifnames`; do wl -i $dev assoclist; done'))
    dev = await component.async_get_wl()
    logger.debug(dev)
    logger.debug("arp")
    logger.debug(await component.connection.async_run_command('arp -n'))
    dev.update(await component.async_get_arp())
    logger.debug(dev)
    logger.debug("neigh")
    logger.debug(await component.connection.async_run_command('ip neigh'))
    dev.update(await component.async_get_neigh(dev))
    logger.debug(dev)
    logger.debug("leases")
    logger.debug(await component.connection.async_run_command(
        'cat /var/lib/misc/dnsmasq.leases'))
    dev.update(await component.async_get_leases(dev))
    logger.debug(dev)


loop = asyncio.get_event_loop()

loop.run_until_complete(print_data())
loop.close()

```
