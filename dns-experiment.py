#!/usr/bin/env python3
import time
import json
from twisted.names import client, dns, error, server
from twisted.internet import reactor
from txjsonrpcqueue.steem import NodeMonitorInjector

class FastestNodeResolver(object):
    def __init__(self, start_node):
        self.injector = NodeMonitorInjector(start_node)
        self.injector.register_forwarder(self)
        self.fastest_node = start_node
    def inject_host_url(self, url):
        self.fastest_node = url
        print(url)
    def query(self, query, timeout=None):
        if query.type == dns.TXT:
            response = self.fastest_node
            payload = dns.Record_TXT(response.encode("utf8"), ttl=90)
            answer = dns.RRHeader(query.name.name, type=dns.TXT, cls=dns.IN, ttl=90, payload=payload)
            return [answer], [], []
        else:
            return defer.fail(error.DomainError())

factory = server.DNSServerFactory( clients=[FastestNodeResolver("https://api.steemit.com")])

protocol = dns.DNSDatagramProtocol(controller=factory)

reactor.listenUDP(8053, protocol, interface="192.168.178.46")

reactor.run()


