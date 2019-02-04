"""Asyncio RpcForwarder implementation"""
#pylint: disable=missing-docstring
import json
import asyncio
import aiohttp
from txjsonrpcqueue.exception import HttpServerError, HttpClientError, JsonRpcBatchError
from txjsonrpcqueue.exception import JsonRpcCommandError, JsonRpcCommandResponseError


class RpcForwarder:
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
            #Register ourselves with the host injector object. Don't start yet untill the host
            # injector injects us with an initial host.
            host_injector.register_forwarder(self)
        else:
            #Set our static host url and start processing batches imediately.
            self.host_url = host_url
            self._fetch_batch()
    def inject_host_url(self, url):
        #Set the host url to its new value
        self.host_url = url
        #If we weren't started yet, start fetching batches now.
        if not self.started:
            self._fetch_batch()
    def _process_batch(self, batch_fut):
        #Map from JSON-RPC to future waiting for result
        futures_map = dict()
        #The outgoing JSON-RPC batch
        batch_out = list()
        #Set of unprocessed entries
        unprocessed = set()
        #Start a new session (may want to look into reusing strategy here)
        session = aiohttp.ClientSession()
        def process_response(response):
            code = 200
            def process_batch_level_exception(exception):
                """Spread batch level exception to each of the batch entries"""
                #On a batch level exception, forward the cought exception to the future for
                # each of the commands that are part of the batch.
                #pylint: disable=unused-variable
                for key, entry_future in futures_map.items():
                    entry_future.set_exception(exception)
            def process_json_parse_error(code, body):
                """Convert a json parse error and HTTP error code into appropriate exception type"""
                if code > 499: #5xx server side error codes
                    process_batch_level_exception(HttpServerError(code, body))
                else:
                    if code > 399: #4xx client side errors.
                        process_batch_level_exception(
                            HttpClientError(code, body))
                    else:
                        # Non-error code in the 2xx and 3xx range.
                        process_batch_level_exception(
                            JsonRpcBatchError(code, body,
                                              "Invalid JSON returned by server"))
            def close_session(session):
                """Asynchonically close the session"""
                def on_closed(result):
                    #pylint: disable=broad-except
                    try:
                        result.result()
                    except Exception:
                        pass
                close_future = asyncio.ensure_future(session.close())
                close_future.add_done_callback(on_closed)
            def process_body(text_result):
                """Process JSON-RPC batch response body"""
                def process_response_json(resp_json):
                    """Process JSON-RPC batch response body JSON content."""
                    #pylint: disable=broad-except
                    try:
                        #Parse the JSON content of the JSON-RPC batch response.
                        resp_obj = json.loads(resp_json)
                    except json.decoder.JSONDecodeError:
                        process_json_parse_error(code, resp_json)
                        resp_obj = []
                    #Assert the parsed JSON is a list.
                    if not isinstance(resp_obj, list):
                        process_batch_level_exception(
                            JsonRpcBatchError(code, resp_json,
                                              "Non-batch JSON response from server."))
                        resp_obj = []
                    #Process the individual command responses
                    for response in resp_obj:
                        #Get the id from the response to match with the apropriate reuest
                        if "id" in response and response["id"] in unprocessed:
                            query_id = response["id"]
                            #Maintain list of unprocessed id's
                            unprocessed.remove(query_id)
                            #Look up the proper command future to map this response to.
                            query_future = futures_map[query_id]
                            #Distinguish between responses and errors.
                            if "result" in response:
                                #Set future result
                                query_future.set_result(response["result"])
                            if (not "result" in response) and "error" in response and \
                                    "message" in response["error"] and \
                                    "code" in response["error"] and \
                                    "data" in response["error"]:
                                query_future.set_exception(
                                    JsonRpcCommandError(response["error"]["code"],
                                                        response["error"]["message"],
                                                        response["error"]["data"]))
                            if (not "result" in response) and (not "error" in response):
                                query_future.set_exception(
                                    JsonRpcCommandResponseError(
                                        "Bad command response from server", response))
                    #Work through any request item id not found in the response.
                    if resp_obj:
                        for no_valid_response_id in unprocessed:
                            query_future = futures_map[no_valid_response_id]
                            error = JsonRpcCommandResponseError(
                                "Request command id not found in response.", resp_obj)
                            query_future.set_exception(error)
                try:
                    text = text_result.result()
                    process_response_json(text)
                #pylint: disable=broad-except
                except Exception as exception:
                    process_batch_level_exception(exception)
                close_session(session)
                self._fetch_batch()
            #Get (text) content from the server response
            try:
                result = response.result()
                code = result.status
                txt = asyncio.ensure_future(result.text())
                txt.add_done_callback(process_body)
            #pylint: disable=broad-except
            except Exception as exception:
                #If the batch JSON-RPC call went wrong, process the batch level exception,
                # close the session and move on to fetching the next batch.
                process_batch_level_exception(exception)
                close_session(session)
                self._fetch_batch()
        #Get the input batch from our invocation argument
        batch_in = batch_fut.result()
        #Build the output batch and futures map.
        for cmd in batch_in:
            self.cmd_id += 1
            unprocessed.add(self.cmd_id)
            newcmd = dict()
            newcmd["id"] = self.cmd_id
            newcmd["jsonrpc"] = "2.0"
            newcmd["method"] = cmd["method"]
            newcmd["params"] = cmd["params"]
            futures_map[self.cmd_id] = cmd["future"]
            batch_out.append(newcmd)
        #Post the JSON-RPC batch request to the server and wait for response
        resp = asyncio.ensure_future(session.post(self.host_url, json=batch_out))
        resp.add_done_callback(process_response)
    def _fetch_batch(self):
        #Notify the queue that we are ready to receive a batch.
        batch_future = self.queue.json_rpcqueue_get()
        batch_future.add_done_callback(self._process_batch)
