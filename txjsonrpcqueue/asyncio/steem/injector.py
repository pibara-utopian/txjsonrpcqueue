#!/usr/bin/env python3
"""Asyncio implementation of the EmbeddedHealthHostInjector.

This class will try to continuously query all known API nodes and test
the response time.
"""

from txjsonrpcqueue.asyncio import Portable
from txjsonrpcqueue.core.steem import MonitorSet, FastestNode

class EmbeddedHealthHostInjector(object):
    """Injector Class that momitors all known STEEM nodes for response times,
       and picks the fastest one"""
    def __init__(self, start_node):
        portable = Portable() #Helper object for making portable code easyer.
        if isinstance(start_node, list):
            #We accept a list of URLs as start node
            self.fnod = FastestNode(start_node[0], self._update_fastest)
            self.monitorset = MonitorSet(start_node, self.fnod, portable)
        else:
            #We also accept a single string.
            self.fnod = FastestNode(start_node, self._update_fastest)
            self.monitorset = MonitorSet([start_node], self.fnod, portable)
        self.forwarders = set()
    def register_forwarder(self, forwarder):
        """Register an RPCForwarder with the injector"""
        self.forwarders.add(forwarder)
    def unregister_forwarder(self, forwarder):
        """Unregister an RPCForwarder"""
        self.forwarders.remove(forwarder)
    def _update_fastest(self, fastest):
        for forwarder in self.forwarders:
            forwarder.inject_host_url(fastest)
