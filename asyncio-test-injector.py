#!/usr/bin/env python3
import time
import json
import asyncio
from txjsonrpcqueue.asyncio.steem import NodeMonitorInjector

class FastestNodeResolver(object):
    def __init__(self, start_node):
        self.injector = NodeMonitorInjector(start_node)
        self.injector.register_forwarder(self)
        self.fastest_node = start_node
    def inject_host_url(self, url):
        self.fastest_node = url
        print(url)

fr = FastestNodeResolver("https://api.steemit.com")

loop = asyncio.get_event_loop()
loop.run_forever()
loop.close()

