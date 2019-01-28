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
from txjsonrpcqueue.corewildcardqueue import WildcardMethod, CoreWildcardQueue
#Import twisted, asyncio or both. At least one of the two should successfully import.
try:
    from txjsonrpcqueue.txwildcardqueue import TxWildcardQueue
    try:
        from txjsonrpcqueue.aiowildcardqueue import AioWildcardQueue
        try:
            from txjsonrpcqueue.aiorpcforwarder import AioRpcForwarder
        except ImportError:
            pass
    except ImportError:
        pass
except ImportError:
    try:
        from txjsonrpcqueue.aiowildcardqueue import AioWildcardQueue, AioRpcForwarder
        try:
            from txjsonrpcqueue.aiorpcforwarder import AioRpcForwarder
        except ImportError:
            pass
    except ImportError:
        raise ImportError("Missing event loop framework (either Twisted or asyncio will do")
