"""Asyncio RpcForwarder implementation"""
#pylint: disable=missing-docstring
import json
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
from twisted.internet import reactor, defer
from txjsonrpcqueue.exception import HttpServerError, HttpClientError, JsonRpcBatchError
from txjsonrpcqueue.exception import JsonRpcCommandError, JsonRpcCommandResponseError

#Simple helper class for JSON-RPC response storage
class _StringProducer(object):
    """Helper class, implements IBodyProducer"""
    #implements(IBodyProducer)
    #pylint: disable=invalid-name
    def __init__(self, body):
        self.body = body
        self.length = len(body)
    def startProducing(self, consumer):
        """startProducing"""
        consumer.write(self.body)
        return defer.succeed(None)
    def pauseProducing(self):
        """dummy pauseProducing, does nothing"""
        pass
    def stopProducing(self):
        """dummy stopProducing, does nothing"""
        pass

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
        #For the twisted implementation we build on twisted.web.client.Agent
        self.agent = Agent(reactor)
        if host_injector:
            #Register ourselves with the host injector object. Don't start yet untill the host
            # injector injects us with an initial host.
            host_injector.register_forwarder(self)
        else:
            #Set our static host url and start processing batches imediately.
            if isinstance(host_url, bytes):
                self.host_url = host_url
            else:
                self.host_url = host_url.encode("utf8")
            self._fetch_batch()
    def inject_host_url(self, url):
        #Set the host url to its new value
        if isinstance(url, bytes):
            self.host_url = url
        else:
            self.host_url = url.encode("utf8")
        #If we weren't started yet, start fetching batches now.
        if not self.started:
            self._fetch_batch()
    def _process_batch(self, batch_in):
        #Map from JSON-RPC to future waiting for result
        deferreds_map = dict()
        #The outgoing JSON-RPC batch
        batch_out = list()
        #Set of unprocessed entries
        unprocessed = set()
        def process_batch_level_exception(exception):
            """Spread batch level exception to each of the batch entries"""
            #On a batch level exception, forward the cought exception to the future for
            # each of the commands that are part of the batch.
            #pylint: disable=unused-variable
            for key, entry_deferred in deferreds_map.items():
                entry_deferred.errback(exception)
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
        def process_response(response):
            code = response.code
            def process_body(text_result):
                """Process JSON-RPC batch response body"""
                #pylint: disable=broad-except, unused-variable
                try:
                    #Parse the JSON content of the JSON-RPC batch response.
                    resp_obj = json.loads(text_result)
                except json.decoder.JSONDecodeError as exception:
                    process_json_parse_error(code, text_result.decode())
                    resp_obj = None
                if resp_obj:
                    #Assert the parsed JSON is a list.
                    if not isinstance(resp_obj, list):
                        process_batch_level_exception(
                            JsonRpcBatchError(code, text_result.decode(),
                                              "Non-batch JSON response from server."))
                        resp_obj = []
                    else:
                        #Process the individual command responses
                        for response in resp_obj:
                            #Get the id from the response to match with the apropriate reuest
                            if "id" in response and response["id"] in unprocessed:
                                query_id = response["id"]
                                #Maintain list of unprocessed id's
                                unprocessed.remove(query_id)
                                #Look up the proper command future to map this response to.
                                query_deferred = deferreds_map[query_id]
                                #Distinguish between responses and errors.
                                if "result" in response:
                                    #Set future result
                                    query_deferred.callback(response["result"])
                                if (not "result" in response) and "error" in response and \
                                        "message" in response["error"] and \
                                        "code" in response["error"] and \
                                        "data" in response["error"]:
                                    query_deferred.errback(
                                        JsonRpcCommandError(response["error"]["code"],
                                                            response["error"]["message"],
                                                            response["error"]["data"]))
                                if (not "result" in response) and (not "error" in response):
                                    query_deferred.errback(
                                        JsonRpcCommandResponseError(
                                            "Bad command response from server", response))
                        #Work through any request item id not found in the response.
                        for no_valid_response_id in unprocessed:
                            query_deferred = deferreds_map[no_valid_response_id]
                            query_deferred.errback(
                                JsonRpcCommandResponseError(
                                    "Request command id not found in response.", resp_obj))
                self._fetch_batch()
            #Get (text) content from the server response
            body_deferred = readBody(response)
            body_deferred.addCallback(process_body)
            body_deferred.addErrback(process_batch_level_exception)
            return body_deferred
        #Build the output batch and deferred map.
        for cmd in batch_in:
            self.cmd_id += 1
            unprocessed.add(self.cmd_id)
            newcmd = dict()
            newcmd["id"] = self.cmd_id
            newcmd["jsonrpc"] = "2.0"
            newcmd["method"] = cmd["method"]
            newcmd["params"] = cmd["params"]
            deferreds_map[self.cmd_id] = cmd["deferred"]
            batch_out.append(newcmd)
        #Post the JSON-RPC batch request to the server and wait for response
        deferred_response = self.agent.request(
            b'POST',
            self.host_url,
            Headers({b"User-Agent"  : [b'TxJsonRpcQueue v0.0.1'],
                     b"Content-Type": [b"application/json"]}),
            _StringProducer(json.dumps(batch_out).encode("utf8")))
        deferred_response.addCallback(process_response)
        deferred_response.addErrback(process_batch_level_exception)
    def _fetch_batch(self):
        #Notify the queue that we are ready to receive a batch.
        batch_deferred = self.queue.json_rpcqueue_get()
        batch_deferred.addCallback(self._process_batch)
