"""Asyncio  WildcardQue implementation"""
#pylint: disable=missing-docstring
import asyncio
from txjsonrpcqueue.corewildcardqueue import WildcardMethod, CoreWildcardQueue

class _AioFutureWrapper(object):
    #pylint: disable=too-few-public-methods
    """Simple wrapper for wrapping a Future with an object that has a 'callback' method"""
    def __init__(self, future):
        self.future = future
    def callback(self, value):
        self.future.set_result(value)

class _AioSoon(object):
    """Helper class for making core hysteresis queue event framework agnostic"""
    # pylint: disable=too-few-public-methods
    def __call__(self, callback, argument):
        asyncio.get_event_loop().call_later(0.0, callback, argument)

def _aio_set_future(dct):
    dct["future"] = asyncio.Future()

def _aio_set_error(dct, err):
    dct["future"].set_exception(err)

class AioWildcardQueue(object):
    # pylint: disable=too-few-public-methods
    """Asyncio based hysteresis queue wrapper"""
    def __init__(self, low=8000, high=10000, highwater=None, lowwater=None, namespace=None):
        #pylint: disable=too-many-arguments
        self.namespace = namespace
        self.core = CoreWildcardQueue(_AioSoon(), low, high, highwater, lowwater)
    def json_rpcqueue_get(self, maxbatch=20):
        """Fetch an entry from the queue, imediately if possible, or remember
           callback for when an entry becomes available."""
        future_get = asyncio.Future()
        self.core.get(_AioFutureWrapper(future_get), maxbatch)
        return future_get
    def __getattr__(self, outername):
        return WildcardMethod(outername, self, _aio_set_future, _aio_set_error)
