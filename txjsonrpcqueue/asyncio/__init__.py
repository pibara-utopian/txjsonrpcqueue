#pylint: disable=missing-docstring
"""Batch oriented JSON-RPC library for Twisted and asyncio.
"""
import asyncio
from txjsonrpcqueue.asyncio.wildcardqueue import WildcardQueue
from txjsonrpcqueue.asyncio.rpcforwarder import RpcForwarder
from txjsonrpcqueue.exception import HttpError, HttpServerError, HttpClientError
from txjsonrpcqueue.exception import JsonRpcBatchError, JsonRpcCommandError
from txjsonrpcqueue.exception import JsonRpcCommandResponseError

#Asyncio implementation of an object with portable operations
class Portable(object):
    #pylint: disable=no-self-use
    def set_callbacks(self, fod, on_ok, on_fail=None, finaly=None):
        """Asyncio implementation of portable callback setter interface."""
        def on_done(res):
            #pylint: disable=broad-except
            try:
                result = res.result()
                on_ok(result)
            except Exception as exception:
                if on_fail:
                    on_fail(exception)
            if finaly:
                finaly()
        fod.add_done_callback(on_done)
    def callLater(self, time, func, *args):
        """Asyncio implementation of portable callLater call interface"""
        #pylint: disable=invalid-name
        asyncio.get_event_loop().call_later(time, func, *args)
    def make_wildcard_queue(self, low=8000, high=10000,
                            highwater=None, lowwater=None, namespace=None):
        """Asyncio implementation of factory method for making a WildcardQueue"""
        #pylint: disable=too-many-arguments
        return WildcardQueue(low, high, highwater, lowwater, namespace)
    def make_rpc_forwarder(self, queue, host_injector=None, host_url=None):
        """Asyncio implementation of factory method for making a RpcForwarder"""
        return RpcForwarder(queue, host_injector, host_url)
