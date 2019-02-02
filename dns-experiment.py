#!/usr/bin/env python3
import time
import json
import OpenSSL
from twisted.names import client, dns, error, server
from twisted.internet import reactor
from txjsonrpcqueue import WildcardQueue, RpcForwarder
from txjsonrpcqueue.exception import  HttpError, HttpServerError, HttpClientError, JsonRpcBatchError, JsonRpcCommandError, JsonRpcCommandResponseError

class FastestNode(object):
    def __init__(self, defaultnode):
        self.node_speed = dict()
        self.node_settime = dict()
        self.best_node = defaultnode
        print("Starting off with node:", defaultnode)
        self.best_speed = 1000000.0
        self.best_settime = 0.0
    def set_node_speed(self, node, speed):
        self.node_speed[node] = speed
        self.node_settime[node] = time.time()
        if speed <= self.best_speed:
            self.best_node = node
            print("New fastest node:", node)
            self.best_speed = speed
            self.best_settime = self.node_settime[node]
        else:
            now = time.time()
            age = now - self.best_settime
            if age > 60 + speed:
                for altnode in self.node_settime:
                    if self.node_speed[altnode] < self.best_speed and \
                            now - self.node_settime[altnode] <= 60 + speed:
                        self.best_node = altnode
                        print("New fastest node:",altnode)
                        self.best_speed = self.node_speed[altnode]
                        self.best_settime = self.node_settime[altnode]

class ApiNodeMonitor(object):
    def __init__(self, url, monitorset, fastest_node):
        self.url = url
        self.monitorset = monitorset
        self.wq = WildcardQueue(low=80, high=100, namespace="condenser_api")
        self.fw = RpcForwarder(queue=self.wq, host_url=url)
        self.ok=None
        self.perm_fail = False
        self.fastest_node = fastest_node
        print("Starting monitor loop for", url)
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
                #'nodes', 'failing_nodes', 'report', 'parameter', 'profile'
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
                reactor.callLater(60, self.tick)
            else:
                if self.perm_fail:
                    #If the failure is likely permanent, wait for 6 hours before our next try
                    reactor.callLater(21600, self.tick)
                    print("Permanent type of error for", self.url, "disabled for 6 hours")
                else:
                    #If the failure is temporary, try again in one hour
                    reactor.callLater(1800, self.tick)
                    print("Temporary type of error for", self.url, "disabled for 30 minutes")
        command_deferred = self.wq.condenser_api.get_accounts(["fullnodeupdate"])
        command_deferred.addCallbacks(process_result, process_error)
        command_deferred.addBoth(set_next_tick)

class MonitorSet(object):
    def __init__(self,initial_set, fastest_node):
        self.fastest_node = fastest_node
        self.monitor_set = dict()
        for initial_node in initial_set:
            self.monitor_set[initial_node] = ApiNodeMonitor(initial_node, self, self.fastest_node)
    def process_node_url(self, url):
        if not url in self.monitor_set:
            print("NEW NODE:", url)
            self.monitor_set[url] = ApiNodeMonitor(url, self, self.fastest_node)


fnod = FastestNode("https://api.steemit.com")
monitorset = MonitorSet([
    'https://api.steemit.com',
    'https://anyx.io',
    'https://steemd.minnowsupportproject.org',
    'https://rpc.steemviz.com',
    'https://api.steemitstage.com',
    'https://api.steem.house',
    'https://steemd.privex.io'],
    fnod)

class FastestNodeResolver(object):
    def __init__(self,fastest_node):
        self.fnod = fastest_node
    def query(self, query, timeout=None):
        if query.type == dns.TXT:
            print("WORKING")
            response = self.fnod.best_node
            print("response:", response)
            payload = dns.Record_TXT(response.encode("utf8"), ttl=90)
            print("payload:", payload)
            answer = dns.RRHeader(query.name.name, type=dns.TXT, cls=dns.IN, ttl=90, payload=payload)
            print("awnser:", answer)
            return [answer], [], []
        else:
            return defer.fail(error.DomainError())

factory = server.DNSServerFactory( clients=[FastestNodeResolver(fnod)])

protocol = dns.DNSDatagramProtocol(controller=factory)

reactor.listenUDP(53, protocol, interface="192.168.178.46")

reactor.run()


