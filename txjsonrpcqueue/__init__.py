#pylint: disable=missing-docstring
"""Batch oriented JSON-RPC library for Twisted and asyncio.
"""
from twisted.internet import reactor
from txjsonrpcqueue.wildcardqueue import WildcardQueue
from txjsonrpcqueue.rpcforwarder import RpcForwarder
from txjsonrpcqueue.exception import HttpError, HttpServerError, HttpClientError
from txjsonrpcqueue.exception import JsonRpcBatchError, JsonRpcCommandError
from txjsonrpcqueue.exception import JsonRpcCommandResponseError

#Twisted implementation of an object with portable operations
class Portable(object):
    #pylint: disable=no-self-use
    def set_callbacks(self, fod, on_ok, on_fail=None, finaly=None):
        """Twisted implementation of portable callback setter interface."""
        def on_failure(failure):
            #pylint: disable=broad-except
            try:
                failure.raiseException()
            except Exception as exception:
                on_fail(exception)
        if on_fail:
            fod.addCallbacks(on_ok, on_failure)
        else:
            fod.addCallback(on_ok)
        if finaly:
            fod.addBoth(finaly)
    def callLater(self, time, func, *args):
        """Twisted implementation of portable callLater call interface"""
        #pylint: disable=no-member,invalid-name
        reactor.callLater(time, func, *args)
    def make_wildcard_queue(self, low=8000, high=10000, highwater=None,
                            lowwater=None, namespace=None):
        """Twisted implementation of factory method for making a WildcardQueue"""
        #pylint: disable=too-many-arguments
        return WildcardQueue(low, high, highwater, lowwater, namespace)
    def make_rpc_forwarder(self, queue, host_injector=None, host_url=None):
        """Twisted implementation of factory method for making a RpcForwarder"""
        return RpcForwarder(queue, host_injector, host_url)
