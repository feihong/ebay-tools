import json


class Logger:
    def __init__(self):
        self.web_logger = None

    def __call__(self, obj):
        print(obj)
        if self.web_logger:
            self.web_logger(obj)


log = Logger()


class WebLogger:
    def __init__(self, loop, sockets):
        self.loop = loop
        self.sockets = sockets

    def __call__(self, obj):
        data = json.dumps(dict(type='log', value=str(obj)))
        for socket in self.sockets:
            self.loop.call_soon_threadsafe(socket.send_str, data)
