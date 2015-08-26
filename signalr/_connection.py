import json

import gevent
import requests

from signalr.transports import get_url

import transports


class Connection:
    def __init__(self, url, cookies, connection_data):
        self.__cookies = cookies
        self.__url = url
        self.__transport = None
        self.__hubs = {}
        self.hub_send_counter = 0
        self.__connection_data = json.dumps(connection_data)

    def __get_transport(self, negotiate_data):
        try_web_sockets = bool(negotiate_data['TryWebSockets'])
        ctor = transports.available_transports['webSockets'] if try_web_sockets else transports.available_transports[
            'serverSentEvents']
        connection_token = negotiate_data['ConnectionToken']

        return ctor(self.__url, self.__cookies, connection_token, self.__connection_data)

    def start(self):
        url = get_url(self.__url, 'negotiate')
        negotiate = requests.get(url, cookies=self.__cookies)
        negotiate_data = json.loads(negotiate.content)
        transport = self.__get_transport(negotiate_data)
        listener = transport.start()
        gevent.spawn(listener)
        self.__transport = transport

    def subscribe(self, handler):
        self.__transport.handlers += handler

    def unsubscribe(self, handler):
        self.__transport.handlers -= handler

    def send(self, data):
        self.__transport.send(data)

    def hub(self, name):
        if name not in self.__hubs:
            self.__hubs[name] = Hub(name, self)
        return self.__hubs[name]


class Hub:
    def __init__(self, name, connection):
        self.server = HubServer(name, connection)
        self.client = HubClient(name, connection)


class HubServer:
    def __init__(self, name, connection):
        self.name = name
        self.__connection = connection

    def invoke(self, method, data):
        self.__connection.send({
            'H': self.name,
            'M': method,
            'A': [data],
            'I': ++self.__connection.hub_send_counter
        })
        self.__connection.hub_send_counter += 1

    def __getattr__(self, method):
        def _missing(data):
            self.invoke(method, data)

        return _missing


class HubClient(object):
    def __init__(self, name, connection):
        self.name = name
        self.__connection = connection

        def handle(data):
            inner_data = data['M'][0] if 'M' in data and len(data['M']) > 0 else {}
            hub = inner_data['H'] if 'H' in inner_data else ''
            if hub == self.name:
                method = inner_data['M']
                arguments = inner_data['A']
                getattr(self, method)(arguments)

        self.__connection.subscribe(handle)
