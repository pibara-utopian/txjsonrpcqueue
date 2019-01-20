#pylint: disable=missing-docstring
"""Batch oriented JSON-RPC library for Twisted and asyncio.

This library is one of a series of libraries meant to displace the asyncsteem JSON-RPC
library for client side usage of the STEEM JSON-RPC API. This library is meant to only
contain the STEEM independent code in order to make this part of the project usable for
other purposes as well.

This library aims to provide a generic batch oriented JSON-RPC queue with a wildcard
method API.

The 1.0 version of this library is intended to run:

    * With Twisted on Python 2.7
    * With Twisted on Python 3.6
    * With asyncio on Python 3.6

"""
#Import twisted, asyncio or both. At least one of the two should successfully import.
#Set variables that indicate if imports succeeded.
HAS_TWISTED = False
HAS_ASYNCIO = False
try:
    from twisted.internet import task
    from twisted.internet import reactor
    from twisted.internet import defer
    HAS_TWISTED = True
    try:
        import asyncio
        HAS_ASYNCIO = True
    except ImportError:
        pass
except ImportError:
    try:
        import asyncio
        HAS_ASYNCIO = True
    except ImportError:
        raise ImportError("Missing event loop framework (either Twisted or asyncio will do")


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

class _TxSoon(object):
    """Helper class for making core hysteresis queue event framework agnostic"""
    # pylint: disable=too-few-public-methods
    def __call__(self, callback, argument):
        task.deferLater(reactor, 0.0, callback, argument)

def _aio_set_future(dct):
    dct["future"] = asyncio.Future()

def _tx_set_deferred(dct):
    dct["deferred"] = defer.Deferred()

def _aio_set_error(dct, err):
    dct["future"].set_exception(err)

def _tx_set_error(dct, err):
    dct["deferred"].errback(err)

class _WildcardMethod(object):
    def __init__(self, outername, outer, set_future_or_deferred, set_error_on_future_or_deferred):
        self.outername = outername
        self.outer = outer
        self.set_future_or_deferred = set_future_or_deferred
        self.set_error_on_future_or_deferred = set_error_on_future_or_deferred
    def __getattr__(self, innername):
        def _core(*args, **kwargs):
            ttask = dict()
            if self.outername:
                ttask["method"] = self.outername + "." + innername
            else:
                ttask["method"] = innername
            if kwargs:
                ttask["params"] = kwargs
            else:
                ttask["params"] = list(args)
            self.set_future_or_deferred(ttask)
            ok = self.outer.core.put(ttask)
            if not ok:
                self.set_error_on_future_or_deferred(ttask, 
                    BufferError("No more room left in WildcardQueue"))
            return ttask["deferred"]
        return _core
    def __call__(self, *args, **kwargs):
        return self.outer.__getattr__(
            self.outer.namespace).__getattr__(self.outername)(*args, **kwargs)

class AioWildcardQueue(object):
    # pylint: disable=too-few-public-methods
    """Asyncio based hysteresis queue wrapper"""
    def __init__(self, low=8000, high=10000, highwater=None, lowwater=None, namespace=None):
        self.namespace = namespace
        if not HAS_ASYNCIO:
            raise RuntimeError("Can not instantiate AioWildcardQueue without asyncio")
        self.core = _CoreWildcardQueue(_AioSoon(), low, high, highwater, lowwater)
    def _get(self, maxbatch=20):
        """Fetch an entry from the queue, imediately if possible, or remember
           callback for when an entry becomes available."""
        f = asyncio.Future()
        self.core.get(_AioFutureWrapper(f), maxbatch)
        return f
    def __getattr__(self, outername):
        return _WildcardMethod(outername, self, _aio_set_future, _aio_set_error)

class TxWildcardQueue(object):
    # pylint: disable=too-few-public-methods
    """Twisted based hysteresis queue wrapper"""
    def __init__(self, low=8000, high=10000, highwater=None, lowwater=None, namespace=None):
        self.namespace = namespace
        if not HAS_TWISTED:
            raise RuntimeError("Can not instantiate TxWildcardQueue without twisted")
        self.core = _CoreWildcardQueue(_TxSoon(), low, high, highwater, lowwater)
    def _get(self, maxbatch=20):
        """Fetch an entry from the queue, imediately if possible,
           or remember callback for when an entry becomes available."""
        d = defer.Deferred()
        self.core.get(d, maxbatch)
        return d
    def __getattr__(self, outername):
        return _WildcardMethod(outername, self, _tx_set_deferred, _tx_set_error)

class _CoreWildcardQueue(object):
    """Simple Twisted based hysteresis queue"""
    def __init__(self, soon, low, high, highwater, lowwater):
        self.soon = soon
        self.low = low
        self.high = high
        self.active = True
        self.highwater = highwater
        self.lowwater = lowwater
        self.msg_queue = list()
        self.fetch_msg_queue = list()
        self.dropcount = 0
        self.okcount = 0
    def put(self, entry):
        """Add entry to the queue, returns boolean indicating success
        will invoke callLater if there is a callback pending for the consumer handler."""
        #Return false imediately if inactivated dueue to hysteresis setting.
        if self.active is False:
            self.dropcount += 1
            return False
        self.okcount += 1
        try:
            #See if there is a callback waiting already
            d = self.fetch_msg_queue.pop(0)
        except IndexError:
            d = None
        if d:
            #If there is a callback waiting schedule for it to be called on
            # the earliest opportunity
            self.soon(d.callback, entry)
            return True
        else:
            #If no callback is waiting, add entry to the queue
            self.msg_queue.append(entry)
            if len(self.msg_queue) >= self.high:
                # Queue is full now (high watermark, disable adding untill empty.
                self.active = False
                #Call handler of high/low watermark events on earliest opportunity
                self.soon(self.highwater, self.okcount)
                self.okcount = 0
            return True
    def  get(self, d, maxbatch):
        """Fetch an entry from the queue, imediately if possible, or remember callback for when an
           entry becomes available."""
        rbatch = list()
        rval = True
        while rval and len(rbatch) < maxbatch:
            try:
                #See if we can fetch a value from the queue right now.
                rval = self.msg_queue.pop(0)
                rbatch.append(rval)
            except IndexError:
                rval = None
        if rbatch:
            #If we can, call callback at earliest opportunity
            self.soon(d.callback, rbatch)
            if self.active is False and len(self.msg_queue) <= self.low:
                #If adding to the queue was disabled and we just dropped below the low water mark,
                # re-enable the queue now.
                self.active = True
                #Call handler of high/low watermark events on earliest opportunity
                self.soon(self.lowwater, self.dropcount)
                self.dropcount = 0
        else:
            # If the queue was empty, add our callback to the callback queue
            self.fetch_msg_queue.append(d.callback)
