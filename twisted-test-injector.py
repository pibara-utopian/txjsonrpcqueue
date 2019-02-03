#!/usr/bin/env python3
import time
import json
from twisted.internet import reactor
from txjsonrpcqueue.steem import EmbeddedHealthHostInjector

class FastestNodeResolver(object):
    def __init__(self, start_node):
        self.injector = EmbeddedHealthHostInjector(start_node)
        self.injector.register_forwarder(self)
        self.fastest_node = start_node
    def inject_host_url(self, url):
        self.fastest_node = url
        print(url)

fr = FastestNodeResolver("https://api.steemit.com")

reactor.run()

