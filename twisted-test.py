#!/usr/bin/env python3
from twisted.internet import reactor
from txjsonrpcqueue import WildcardQueue, RpcForwarder

def process_result(res):
    print("#########################################################")
    print(res)
    print("---------------------------------------------------------")

def oops(e):
    print("OOPS:",e)

wq = WildcardQueue(low=8000, high=10000, namespace="condenser_api")
fw = RpcForwarder(queue=wq, host_url="https://api.steemit.com")
for index in range(12345670,12345679):
    d1 = wq.get_block(index)
    d1.addCallbacks(process_result, oops)
    d2 = wq.block_api.get_block(block_num=index)
    d2.addCallbacks(process_result, oops)
d3 = wq.block_api.bogus_api_call(block_num=index)
d3.addCallbacks(process_result, oops)

reactor.run()

