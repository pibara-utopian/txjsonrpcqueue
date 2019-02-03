#!/usr/bin/env python3
import time
import json
import asyncio
from txjsonrpcqueue.asyncio import WildcardQueue, RpcForwarder
from txjsonrpcqueue.exception import  HttpError, HttpServerError, HttpClientError, JsonRpcBatchError, JsonRpcCommandError, JsonRpcCommandResponseError


class _FastestNode(object):
    def __init__(self, defaultnode, inject):
        self.node_speed = dict()
        self.node_settime = dict()
        self.best_node = defaultnode
        self.inject = inject
        self.best_speed = 1000000.0
        self.best_settime = 0.0
    def set_node_speed(self, node, speed):
        self.node_speed[node] = speed
        self.node_settime[node] = time.time()
        if speed <= self.best_speed:
            if self.best_node != node:
                self.inject(node)
            self.best_node = node
            self.best_speed = speed
            self.best_settime = self.node_settime[node]
        else:
            now = time.time()
            age = now - self.best_settime
            if age > 60 + speed:
                oldnode = self.best_node
                for altnode in self.node_settime:
                    if self.node_speed[altnode] < self.best_speed and \
                            now - self.node_settime[altnode] <= 60 + speed:
                        self.best_node = altnode
                        self.best_speed = self.node_speed[altnode]
                        self.best_settime = self.node_settime[altnode]
                if oldnode != self.best_node:
                    self.inject(self.best_node)

class _ApiNodeMonitor(object):
    def __init__(self, url, monitorset, fastest_node):
        self.url = url
        self.monitorset = monitorset
        self.wq = WildcardQueue(low=80, high=100, namespace="condenser_api")
        self.fw = RpcForwarder(queue=self.wq, host_url=url)
        self.ok=None
        self.perm_fail = False
        self.fastest_node = fastest_node
        self.tick()
    def tick(self):
        start_time = time.time()
        def process_result(result):
            try:
                obj = json.loads(result[0]["json_metadata"])
                nodes = list(set(obj["nodes"] +  list(obj["failing_nodes"].keys()) + [x["node"] for x in obj["report"]]))
                filtered_nodes = [x for x in nodes if x[:6] == "https:"]
                for filtered_node in filtered_nodes:
                    self.monitorset.process_node_url(filtered_node)
            except Exception as e:
                print(e)
            self.ok = True
        def process_error(error):
            self.ok = False
            try:
                error.raiseException()
            except HttpServerError as e:
                self.perm_fail = False
            except HttpClientError as e:
                self.perm_fail = True
            except Exception as e:
                self.perm_fail = False
            self.ok = False
        def set_next_tick(hmm=None):
            response_time = time.time() - start_time
            if self.ok:
                #Everything was OK, do a new test in a minute.
                self.fastest_node.set_node_speed(self.url, response_time)
                asyncio.get_event_loop().call_later(60, self.tick)
            else:
                if self.perm_fail:
                    #If the failure is likely permanent, wait for 6 hours before our next try
                    asyncio.get_event_loop().call_later(21600, self.tick)
                else:
                    #If the failure is temporary, try again in one hour
                    asyncio.get_event_loop().call_later(1800, self.tick)
        def on_done(res):
            try:
                result = res.result()
                process_result(result)
            except Exception as exception:
                process_error(exception)
            set_next_tick()
        command_future = self.wq.condenser_api.get_accounts(["fullnodeupdate"])
        command_future.add_done_callback(on_done)

class _MonitorSet(object):
    def __init__(self,initial_set, fastest_node):
        self.fastest_node = fastest_node
        self.monitor_set = dict()
        for initial_node in initial_set:
            self.monitor_set[initial_node] = _ApiNodeMonitor(initial_node, self, self.fastest_node)
    def process_node_url(self, url):
        if not url in self.monitor_set:
            self.monitor_set[url] = _ApiNodeMonitor(url, self, self.fastest_node)

class NodeMonitorInjector(object):
    def __init__(self, start_node):
        self.fnod = _FastestNode(start_node, self.update_fastest)
        self.monitorset = _MonitorSet([start_node],self.fnod)
        self.forwarders = set()
    def register_forwarder(self,forwarder):
        self.forwarders.add(forwarder)
    def unregister_forwarder(self,forwarder):
        self.forwarders.remove(forwarder)
    def update_fastest(self, fastest):
        for forwarder in self.forwarders:
            forwarder.inject_host_url(fastest)

