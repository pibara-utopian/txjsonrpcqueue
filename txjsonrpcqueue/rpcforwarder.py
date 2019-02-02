"""Asyncio RpcForwarder implementation"""
#pylint: disable=missing-docstring
import json
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
from twisted.internet import reactor, defer

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
        self.agent = Agent(reactor)
        if host_injector:
            #Register ourselves with the host injector object. Don't start yet untill the host
            # injector injects us with an initial host.
            host_injector.register_forwarder(self)
        else:
            #Set our static host url and start processing batches imediately.
            if isinstance(host_url, str):
                self.host_url = host_url.encode("utf8")
            else:
                self.host_url = host_url
            self._fetch_batch()
    def inject_host_url(self, url):
        #Set the host url to its new value
        self.host_url = url
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
        def process_response(response):
            def process_body(text_result):
                """Process JSON-RPC batch response body"""
                try:
                    #Parse the JSON content of the JSON-RPC batch response.
                    resp_obj = json.loads(text_result)
                    #pylint: disable=broad-except
                except Exception as exception:
                    process_batch_level_exception(exception)
                    resp_obj = None
                if resp_obj:
                    #Assert the parsed JSON is a list.
                    if not isinstance(resp_obj, list):
                        process_batch_level_exception(
                            RuntimeError("Non-batch JSON response from server " \
                                + self.host_url + " : " + text_result))
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
                                else:
                                    if "error" in response and "message" in response["error"]:
                                        query_deferred.errback(
                                            RuntimeError(response["error"]["message"]))
                                    else:
                                        query_deferred.errback(
                                            RuntimeError(
                                                "Neither result nor valid error field "\
                                                + "in response from server "\
                                                + self.host_url + " :" + text_result))
                        #Work through any request item id not found in the response.
                        for no_valid_response_id in unprocessed:
                            query_future = deferreds_map[no_valid_response_id]
                            query_future.errback(
                                RuntimeError(
                                    "Bad JSON-RPC response from server " \
                                    + self.host_url \
                                    + ", request command id not found in response."))
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
