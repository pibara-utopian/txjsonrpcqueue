"""Shared code between WildcardQue implementations for asyncio and twisted"""

class WildcardMethod(object):
    """Wildcard method shared code with namespace support."""
    #pylint: disable=too-few-public-methods
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
            put_ok = self.outer.core.put(ttask)
            if not put_ok:
                self.set_error_on_future_or_deferred(ttask,
                                                     BufferError(
                                                         "No more room left in WildcardQueue"))
            if "deferred" in ttask:
                return ttask["deferred"]
            return ttask["future"]
        return _core
    def __call__(self, *args, **kwargs):
        return self.outer.__getattr__(
            self.outer.namespace).__getattr__(self.outername)(*args, **kwargs)

class CoreWildcardQueue(object):
    """Simple Twisted based hysteresis queue"""
    #pylint: disable=too-many-instance-attributes
    def __init__(self, soon, low, high, highwater, lowwater):
        #pylint: disable=too-many-arguments
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
            deferred_get = self.fetch_msg_queue.pop(0)
        except IndexError:
            deferred_get = None
        if deferred_get:
            #If there is a callback waiting schedule for it to be called on
            # the earliest opportunity
            self.soon(deferred_get.callback, [entry])
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
    def again(self, batch):
        self.msg_queue = batch + self.msg_queue
    def get(self, deferred_get, maxbatch):
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
            self.soon(deferred_get.callback, rbatch)
            if self.active is False and len(self.msg_queue) <= self.low:
                #If adding to the queue was disabled and we just dropped below the low water mark,
                # re-enable the queue now.
                self.active = True
                #Call handler of high/low watermark events on earliest opportunity
                self.soon(self.lowwater, self.dropcount)
                self.dropcount = 0
        else:
            # If the queue was empty, add our callback to the callback queue
            self.fetch_msg_queue.append(deferred_get)
