# txjsonrpcqueue : Asynchonous (Twisted or asyncio) Python library for batched JSON-RPC

The txjsonrpcqueue library currently is in early stages of development. The goal is to do
a rewrite of the functionality of the asyncsteem library and the asyncsteem3 library in a 
set of seperate smaller libraries. This library implementing the low level asynchronous 
JSON-RPC functionality. A second library for streaming new or old blocks, and a third library
implementing signed operations. The goal is to make all three libraries work across python 
versions and across event frameworks.

* Python >= 2.6 with Twisted
* Python >= 3.3 with Twisted
* Python >= 3.6 with asyncio

While support of the STEEM APPBASE API is a prime support, the goal for txjsonrpcqueue, other 
than the other two libraries is to be usable outside of the context of STEEM APPBASE.

```python
#Import WildcardQueue and JsonRpcClient in their Twisted variant. 
# ( Alternatively you might get the asyncio variants if you really don't want to use Twisted)
from txjsonrpcqueue import TxWildcardQueue as WildcardQueue
from txjsonrpcqueue import TxJsonRpcClient as JsonRpcClient

#Create a queue for JSON-RPC batch operations. The queue is a hysteresis queue. That means
#the queue will fill up to the max size of high and then, while the client is empty emptying
#the queue, new commands will error out untill the low water mark has been reached again.
#The API also has the possibility to set hooks for logging high and low water marks.
#Note that as this library is meant to become usable outside of STEEM APPBASE, you do need
#to specify "condenser_api"as default namespace for use with STEEM.
#If you wish to use this library with a JSON-RPC server that does support batches but does not 
#use a namespaced API, you can leave defaultns defined as its default of None. 
wq = WildcardQueue(low=8000, high=10000, defaultns="condenser_api")

#Now that we have a queue, we can define our core JSON-RPC client that will get fed by the queue.
client = JsonRpcClient(nodes=["api.steemitstage.com"],queue=wq)

#The wildcard queue will map any method as called to a JSONRPC call in the default namespace if no 
#namespace is used in invocation. Doing the same with the AioWildcardQueue will get you a Future 
#instead.
d1 = wq.get_block(123456)
d1.addCallback(process_block)
d1.addErrback(oops_block)

#If you want to instead call a JSON-RPC method in a specific namespace, you can do that to and the
#library will again provide the syntax for adding your command to a future batch of asynchonous 
#operations. Again like before you get back a deferred. Again doing the same with the AioWildcardQueue 
#will get you a Future instead.
d2 = wq.block_api.get_block(block_num=123456)
d2.addCallback(process_block)
d2.addErrback(oops_block)
```

