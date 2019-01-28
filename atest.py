#!/usr/bin/env python3
import asyncio
from txjsonrpcqueue import AioWildcardQueue as WildcardQueue
from txjsonrpcqueue import AioRpcForwarder as RpcForwarder

def process_result(result):
    try:
        res = result.result()
        pass
        print("#########################################################")
        print(res)
        print("---------------------------------------------------------")
    except Exception as e:
        print("OOPS:",e)

wq = WildcardQueue(low=8000, high=10000, namespace="condenser_api")
fw = RpcForwarder(queue=wq, host_url="https://api.steemit.com")
for index in range(12345670,12345679):
    f1 = wq.get_block(index)
    f1.add_done_callback(process_result)
    f2 = wq.block_api.get_block(block_num=index)
    f2.add_done_callback(process_result)
f3 = wq.block_api.bogus_api_call(block_num=index)
f3.add_done_callback(process_result)
loop = asyncio.get_event_loop()
loop.run_forever()
loop.close()

