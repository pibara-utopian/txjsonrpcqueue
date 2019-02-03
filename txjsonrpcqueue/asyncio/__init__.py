#pylint: disable=missing-docstring
"""Batch oriented JSON-RPC library for Twisted and asyncio.
"""
import asyncio
from txjsonrpcqueue.asyncio.wildcardqueue import WildcardQueue
from txjsonrpcqueue.asyncio.rpcforwarder import RpcForwarder
from txjsonrpcqueue.exception import HttpError, HttpServerError, HttpClientError, JsonRpcBatchError, JsonRpcCommandError, JsonRpcCommandResponseError

#Asyncio implementation of an object with portable operations
class Portable(object):
    def set_callbacks(self, fod, on_ok, on_fail=None, finaly=None):
        def on_done(res):
            try:
                result = res.result()
                on_ok(result)
            except Exception as exception:
                if (on_fail):
                    on_fail(exception)
            if finaly:
                finaly()
        fod.add_done_callback(on_done)
    def callLater(self, time, func, *args):
        asyncio.get_event_loop().call_later(time, func, *args)
    def makeWildcardQueue(self,low=8000, high=10000, highwater=None, lowwater=None, namespace=None):
        return WildcardQueue(low, high, highwater, lowwater, namespace)
    def makeRpcForwarder(self, queue, host_injector=None, host_url=None):
        return RpcForwarder(queue, host_injector, host_url)
