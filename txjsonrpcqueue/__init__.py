#pylint: disable=missing-docstring
"""Batch oriented JSON-RPC library for Twisted and asyncio.
"""
from twisted.internet import reactor
from txjsonrpcqueue.wildcardqueue import WildcardQueue
from txjsonrpcqueue.rpcforwarder import RpcForwarder
from txjsonrpcqueue.exception import HttpError, HttpServerError, HttpClientError, JsonRpcBatchError, JsonRpcCommandError, JsonRpcCommandResponseError

#Twisted implementation of an object with portable operations
class Portable(object):
    def set_callbacks(self, fod, on_ok, on_fail=None, finaly=None):
        if on_fail:
            fod.addCallbacks(on_ok, on_fail)
        else:
            fod.addCallback(on_ok)
        if finaly:
            fod.addBoth(finaly)
    def callLater(self, time, func, *args):
        reactor.callLater(time, func, *args)
    def makeWildcardQueue(self, low=8000, high=10000, highwater=None, lowwater=None, namespace=None):
        return WildcardQueue(low, high, highwater, lowwater, namespace)
    def makeRpcForwarder(self, queue, host_injector=None, host_url=None):
        return RpcForwarder(queue, host_injector, host_url)

