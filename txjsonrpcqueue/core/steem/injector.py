#!/usr/bin/env python3
"""Core implementation of Host Injector classes"""
import time
import json
from txjsonrpcqueue.exception import HttpClientError


class FastestNode(object):
    #pylint: disable=too-few-public-methods
    """Helper class for keeping track of the fastest node."""
    def __init__(self, defaultnode, inject):
        self.node_speed = dict()
        self.node_settime = dict()
        self.best_node = defaultnode
        self.inject = inject
        self.best_speed = 1000000.0
        self.best_settime = 0.0
    def set_node_speed(self, node, speed):
        """Set the node speed for a specific node URL"""
        self.node_speed[node] = speed
        self.node_settime[node] = time.time()
        if speed <= self.best_speed:
            #There is no dispute, this is the fastest node
            if self.best_node != node:
                #Only inject if we weren't already the fastest before.
                self.inject(node)
            self.best_node = node
            self.best_speed = speed
            self.best_settime = self.node_settime[node]
        else:
            #There have been faster nodes, at some point
            now = time.time()
            age = now - self.best_settime
            if age > 60 + speed:
                # If the fastest time is older than one minute plus our current response time,
                # we check if we need to update the fastest node.
                #
                # Remember the previous best node for later reference
                oldnode = self.best_node
                #First assume 'this' node is the fastest
                self.best_node = node
                self.best_speed = speed
                self.best_settime = self.node_settime[node]
                #itterate over all nodes previously seen
                for altnode in self.node_settime:
                    if self.node_speed[altnode] < self.best_speed and \
                            now - self.node_settime[altnode] <= 60 + speed:
                        #If an other faster node was seen recently, set that one as fastest.
                        self.best_node = altnode
                        self.best_speed = self.node_speed[altnode]
                        self.best_settime = self.node_settime[altnode]
                #Only inject if the new fastest node is an other node than the one before
                if oldnode != self.best_node:
                    self.inject(self.best_node)

class _ApiNodeMonitor(object):
    #pylint: disable=too-many-instance-attributes,too-few-public-methods
    def __init__(self, url, monitorset, fastest_node, portable):
        self.url = url
        self.monitorset = monitorset
        self.wque = portable.make_wildcard_queue(low=80, high=100, namespace="condenser_api")
        self.fwdr = portable.make_rpc_forwarder(queue=self.wque, host_url=url)
        self.state_ok = None
        self.perm_fail = False
        self.fastest_node = fastest_node
        self.portable = portable
        self.tick()
    def tick(self):
        """Timer tick event handler, start a new query for this monitor"""
        start_time = time.time()
        def process_result(result):
            """Process result from condenser_api.get_accounts call"""
            #pylint: disable=broad-except
            try:
                #Try to get a list of node candidate from the @fulnodeupdate account json_metadata.
                obj = json.loads(result[0]["json_metadata"])
                nodes = list(set(obj["nodes"] +  list(obj["failing_nodes"].keys()) + \
                    [x["node"] for x in obj["report"]]))
                #We only know how to deal with https nodes at the moment.
                filtered_nodes = [x for x in nodes if x[:6] == "https:"]
                for filtered_node in filtered_nodes:
                    #There may be new nodes in here
                    self.monitorset.process_node_url(filtered_node)
            except Exception as exception:
                pass
                #print(exception)
            self.state_ok = True
        def process_error(error):
            """Process error from condenser_api.get_accounts call"""
            self.state_ok = False
            if isinstance(error, HttpClientError):
                self.perm_fail = True
        def set_next_tick(hmm=None):
            """Set timer for triggering the next API node polling action"""
            #pylint: disable=unused-argument
            response_time = time.time() - start_time
            if self.state_ok:
                #Everything was OK, do a new test in a minute.
                self.fastest_node.set_node_speed(self.url, response_time)
                self.portable.callLater(60, self.tick)
            else:
                if self.perm_fail:
                    #If the failure is likely permanent, wait for 6 hours before our next try
                    self.portable.callLater(21600, self.tick)
                else:
                    #If the failure is temporary, try again in one hour
                    self.portable.callLater(1800, self.tick)
        #Request account info from the @fullnodeupdate account.
        command_deferred_or_future = self.wque.condenser_api.get_accounts(["fullnodeupdate"])
        self.portable.set_callbacks(command_deferred_or_future,
                                    process_result, process_error, set_next_tick)

class MonitorSet(object):
    """Collection of node monitor objects"""
    #pylint: disable=too-few-public-methods
    def __init__(self, initial_set, fastest_node, portable):
        self.fastest_node = fastest_node
        self.monitor_set = dict()
        self.portable = portable
        for initial_node in initial_set:
            self.monitor_set[initial_node] = _ApiNodeMonitor(initial_node,
                                                             self,
                                                             self.fastest_node,
                                                             self.portable)
    def process_node_url(self, url):
        """Process node URL from @fullnodeupdate json meta"""
        if not url in self.monitor_set:
            self.monitor_set[url] = _ApiNodeMonitor(url,
                                                    self,
                                                    self.fastest_node,
                                                    self.portable)
