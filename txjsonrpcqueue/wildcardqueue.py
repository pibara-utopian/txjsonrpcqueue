"""Twisted  WildcardQue implementation"""
#pylint: disable=missing-docstring
from twisted.internet import task
from twisted.internet import reactor
from twisted.internet import defer
from txjsonrpcqueue.core.wildcardqueue import WildcardMethod, CoreWildcardQueue

class _TxSoon(object):
    """Helper class for making core hysteresis queue event framework agnostic"""
    # pylint: disable=too-few-public-methods
    def __call__(self, callback, argument):
        task.deferLater(reactor, 0.0, callback, argument)

def _tx_set_deferred(dct):
    dct["deferred"] = defer.Deferred()

def _tx_set_error(dct, err):
    dct["deferred"].errback(err)

class WildcardQueue(object):
    # pylint: disable=too-few-public-methods
    """Twisted based hysteresis queue wrapper"""
    def __init__(self, low=8000, high=10000, highwater=None, lowwater=None, namespace=None):
        #pylint: disable=too-many-arguments
        self.namespace = namespace
        self.core = CoreWildcardQueue(_TxSoon(), low, high, highwater, lowwater)
    def json_rpcqueue_get(self, maxbatch=10):
        """Fetch an entry from the queue, imediately if possible,
           or remember callback for when an entry becomes available."""
        deferred_get = defer.Deferred()
        self.core.get(deferred_get, maxbatch)
        return deferred_get
    def json_rpcqueue_again(self, batch):
        self.core.again(batch)
    def __getattr__(self, outername):
        return WildcardMethod(outername, self, _tx_set_deferred, _tx_set_error)
