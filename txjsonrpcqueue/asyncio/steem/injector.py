#!/usr/bin/env python3
import time
import json
from txjsonrpcqueue.asyncio import Portable
from txjsonrpcqueue.core.steem import MonitorSet, FastestNode

class EmbeddedHealthHostInjector(object):
    def __init__(self, start_node):
        portable = Portable()
        self.fnod = FastestNode(start_node, self.update_fastest)
        self.monitorset = MonitorSet([start_node],self.fnod, portable)
        self.forwarders = set()
    def register_forwarder(self,forwarder):
        self.forwarders.add(forwarder)
    def unregister_forwarder(self,forwarder):
        self.forwarders.remove(forwarder)
    def update_fastest(self, fastest):
        for forwarder in self.forwarders:
            forwarder.inject_host_url(fastest)

