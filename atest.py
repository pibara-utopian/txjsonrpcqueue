#!/usr/bin/env python3
import asyncio
from txjsonrpcqueue import AioWildcardQueue as WildcardQueue
from txjsonrpcqueue import AioRpcForwarder as RpcForwarder

wq = WildcardQueue(low=8000, high=10000, namespace="condenser_api")
fw = RpcForwarder(queue=wq, host_url="https://api.steemit.com")
for index in range(123450,123470):
    wq.get_block(index)
    wq.block_api.get_block(block_num=index)
wq.block_api.bogus_api_call(block_num=index)
loop = asyncio.get_event_loop()
loop.run_forever()
loop.close()

