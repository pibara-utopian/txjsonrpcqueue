"""Twisted  WildcardQue implementation"""
#pylint: disable=missing-docstring
import asyncio
import aiohttp
import json
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
    def _get(self, maxbatch=20):
        """Fetch an entry from the queue, imediately if possible, or remember
           callback for when an entry becomes available."""
        future_get = asyncio.Future()
        self.core.get(_AioFutureWrapper(future_get), maxbatch)
        return future_get
    def __getattr__(self, outername):
        return WildcardMethod(outername, self, _aio_set_future, _aio_set_error)

class AioRpcForwarder(object):
    # pylint: disable=too-few-public-methods
    def __init__(self, queue, host_injector=None, host_url=None):
        if host_injector is None and host_url is None:
            raise RuntimeError("Constructor requires either host_injector or host_url to be set.")
        if host_injector and host_url:
            raise RuntimeError("Either host_injector or host_url should be specified, not both")
        self.queue = queue
        self.cmd_id = 0
        self.started = False
        if host_injector:
            #Register ourselves with the host injector object. Don't start yet untill the host injector
            #injects us with an initial host.
            host_injector.register_forwarder(self)
        else:
            #Set our static host url and start processing batches imediately.
            self.host_url = host_url
            self._fetch_batch()
    def inject_host_url(self,url):
        #Set the host url to its new value
        self.host_url = url
        #If we weren't started yet, start fetching batches now.
        if not self.started:
            self._fetch_batch()
    def _fetch_batch(self):
        def process_batch(batch_fut):
            futures_map = dict()
            batch_out = list()
            session = aiohttp.ClientSession()
            def process_response(response):
                def process_batch_level_exception(exception):
                    print(exception)
                def close_session(session):
                    def on_closed(result):
                        try:
                            result.result()
                        except Exception as e:
                            print("Problem closing:",e)
                    close_future = asyncio.ensure_future(session.close())
                    close_future.add_done_callback(on_closed)
                def process_text(text_result):
                    def process_response_json(resp_json):
                        try:
                            resp_obj = json.loads(resp_json)
                            if not isinstance(resp_obj,list):
                                process_batch_level_exception(RuntimeError("Non-batch JSON response from server " + self.host_url))
                            for response in resp_obj:
                                if "id" in response:
                                    query_id = response["id"]
                                    if query_id in futures_map:
                                        query_future = futures_map[query_id]
                                        if "result" in response:
                                            query_future.set_result(response["result"])
                                        else:
                                            if "error" in response:
                                                error = response["error"]
                                                if "message" in error:
                                                    msg = error["message"]
                                                    query_future.set_exception(RuntimeError(msg))
                                                else:
                                                    query_future.set_exception(RuntimeError("Error without message field from server " + self.host_url))
                                            else:
                                                print("PROBLEM: neither result nor error field in response", response)
                                    else:
                                        print("PROBLEM: no id field in response:", response)
                                else:
                                    print("PROBLEM: id field in response does not match any id field in this batch:", response)
                        except Exception as e:
                            process_batch_level_exception(e)
                    try:
                        text = text_result.result()
                        process_response_json(text)
                    except Exception as e:
                        process_batch_level_exception(e)
                    close_session(session)
                    self._fetch_batch()
                try:
                    result = response.result()
                    txt = asyncio.ensure_future(result.text())
                    txt.add_done_callback(process_text)
                except Exception as e:
                    process_batch_level_exception(e)
                    close_session(session)
                    self._fetch_batch()

            batch_in=batch_fut.result()
            for cmd in batch_in:
                self.cmd_id += 1
                newcmd = dict()
                newcmd["id"] = self.cmd_id
                newcmd["jsonrpc"] = "2.0"
                newcmd["method"] = cmd["method"]
                newcmd["params"] = cmd["params"]
                futures_map[self.cmd_id] = cmd["future"]
                batch_out.append(newcmd)
            resp = asyncio.ensure_future(session.post(self.host_url, json=batch_out))
            resp.add_done_callback(process_response)
        #Notify the queue that we are ready to receive a batch.
        batch_future = self.queue._get()
        batch_future.add_done_callback(process_batch)


        
