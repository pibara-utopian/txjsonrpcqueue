class HttpError(Exception):
    def __init__(self, code, body):
        super(HttpError, self).__init__("HTTP Error; code " + str(code))
        self.code = code
        self.body = body

class HttpServerError(HttpError):
    def __init__(self, code, body):
        super(HttpServerError, self).__init__(code, body)

class HttpClientError(HttpError):
    def __init__(self, code, body):
        super(HttpClientError, self).__init__(code, body)

class JsonRpcBatchError(Exception):
    def __init__(self, code, body, message):
        super(JsonRpcBatchError, self).__init__("Batch Error:" + message)
        self.code = code
        self.body = body

class JsonRpcCommandError(Exception):
    def __init__(self, code, message, data):
        super(JsonRpcCommandError, self).__init__("JSON-RPC Error; code" + str(code) + ":" + message)
        self.code = code
        self.data = data

class JsonRpcCommandResponseError(Exception):
    def __init__(self, message, obj):
        super(JsonRpcCommandResponseError, self).__init__(message)
        self.obj = obj
