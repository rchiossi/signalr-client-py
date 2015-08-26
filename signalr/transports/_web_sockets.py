import json
import urlparse

from websocket import create_connection

from signalr.transports import Transport


class WebSocketsTransport(Transport):
    name = 'webSockets'

    def __init__(self, url, cookies, connection_token, connection_data):
        Transport.__init__(self, self.__get_transport_specific_url(url), cookies, connection_token, connection_data)
        self.ws = None

    def _get_transport_name(self):
        return WebSocketsTransport.name

    @staticmethod
    def __get_transport_specific_url(url):
        parsed = urlparse.urlparse(url)
        scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        url_data = (scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)

        return urlparse.urlunparse(url_data)

    def start(self):
        self.ws = create_connection(self._get_url('connect'), header=self.__get_headers())

        def _receive():
            while True:
                notification = self.ws.recv()
                self._handle_notification(notification)

        return _receive

    def __get_headers(self):
        return map(lambda name: '{name}: {value}'.format(name=name, value=self._headers[name]), self._headers)

    def send(self, data):
        self.ws.send(json.dumps(data))
