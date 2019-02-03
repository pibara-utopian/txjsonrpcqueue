#!/usr/bin/env python3
import time
import json
import sys
from twisted.internet import reactor
import logging
from twisted.python import log
from txjsonrpcqueue.steem import EmbeddedHealthHostInjector

class FastestNodeResolver(object):
    def __init__(self, start_node):
        self.injector = EmbeddedHealthHostInjector(start_node)
        self.injector.register_forwarder(self)
        self.fastest_node = start_node
    def inject_host_url(self, url):
        self.fastest_node = url
        print(url)

log.PythonLoggingObserver().start()
logging.basicConfig(filename="test.log", level=logging.DEBUG)
#observer = textFileLogObserver(sys.stdout)
#logger = Logger(observer=observer,namespace="test")

fr = FastestNodeResolver("https://api.steemit.com")

reactor.run()

