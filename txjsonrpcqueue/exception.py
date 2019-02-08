"""Exceprion classes used by txjsonrpcqueue"""

class SSLError(Exception):
    """Base class for SSL errors"""

class SSLNameMismatch(SSLError):
    """SSL error: dns name mismatch"""

class HttpError(Exception):
    """Base class for HTTP errors"""
    def __init__(self, code, body):
        super(HttpError, self).__init__("HTTP Error; code " + str(code))
        self.code = code
        self.body = body

class HttpServerError(HttpError):
    """5xx HTTP Errors"""
#    def __init__(self, code, body):
#        super(HttpServerError, self).__init__(code, body)

class HttpClientError(HttpError):
    """4xx HTTP errors"""
#    def __init__(self, code, body):
#        super(HttpClientError, self).__init__(code, body)

class JsonRpcBatchError(Exception):
    """Wrongly formatted JSON-RPC response error"""
    def __init__(self, code, body, message):
        super(JsonRpcBatchError, self).__init__("Batch Error:" + message)
        self.code = code
        self.body = body

class JsonRpcCommandError(Exception):
    """Error response on a command from the server"""
    def __init__(self, code, message, data):
        super(JsonRpcCommandError, self).__init__(
            "JSON-RPC Error; code" + str(code) + ":" + message)
        self.code = code
        self.data = data

class JsonRpcCommandResponseError(Exception):
    """Invalid JsonRPC response from server on individual command"""
    def __init__(self, message, obj):
        super(JsonRpcCommandResponseError, self).__init__(message)
        self.obj = obj
