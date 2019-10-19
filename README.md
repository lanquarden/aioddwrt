Async API for [DD-WRT] devices. 

This has been forked from [aioasuswrt] and adapted for [DD-WRT]

[DD-WRT]: https://dd-wrt.com
[aioasuswrt]: https://github.com/kennedyshead/aioasuswrt

## Credits:
[@kennedyshead](https://github.com/kennedyshead)

## Info
This library is mainly intended to be used by [Home Assistant] and more 
specifically the [DD-WRT integration]. It supports three ways to retrieve
information from [DD-WRT] devices:
 * ``http``: the web interface is used, currently ``https`` is not supported.
   This interface does not support multiple wireless interfaces.
 * ``ssh``: the command line interface through ``ssh`` supports multiple
   interfaces and can extract WAN traffic statistics.
 * ``telnet``: the same features as the ``ssh`` interface are supported.

[Home Assistant]: https://www.home-assistant.io/
[DD-WRT integration]: https://www.home-assistant.io/integrations/ddwrt/

## Issues
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

component = DdWrt('bridge.lanquarden.com', protocol='ssh',
                  ssh_key='ssh_key.txt', username='root', password='GEid4g')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def print_data():
    logger.debug("wl")
    dev = await component.async_get_wl()
    logger.debug(f"connected: {dev}")
    logger.debug("leases")
    dev = await component.async_get_leases()
    logger.debug(dev)


async def periodic():
    while True:
        try:
            await print_data()
        except ConnectionError:
            logger.error('Error while connecting')
        await asyncio.sleep(10)

loop = asyncio.get_event_loop()
loop.run_until_complete(periodic())
loop.close()
```
