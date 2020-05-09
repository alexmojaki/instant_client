from functools import partial
from typing import Generic, TypeVar, Union

from datafunctions import datafunction
from jsonrpcclient.client import Client
from jsonrpcclient.clients.http_client import HTTPClient

T = TypeVar("T")


class InstantClient(Generic[T]):
    """
    A type-safe JSON-RPC client with automatic (de)serialization.
    For more info, see https://github.com/alexmojaki/instant_client

    Usage looks like this:

        from dataclasses import dataclass
        from instant_client import InstantClient

        @dataclass
        class Point:
            x: int
            y: int

        class Methods:
            def translate(self, p: Point, dx: int, dy: int) -> Point:
                pass

            def scale(self, p: Point, factor: int) -> Point:
                pass

        methods = InstantClient("http://127.0.0.1:5000/api/", Methods()).methods

        assert methods.scale(Point(1, 2), factor=3) == Point(3, 6)

    While this looks like it just called `Methods.scale()` directly,
    under the hood it sent an HTTP request to a server.
    The same code written more manually looks like this:

        import requests

        response = requests.post(
            'http://127.0.0.1:5000/api/',
            json={
                'id': 0, 
                'jsonrpc': '2.0', 
                'method': 'scale', 
                'params': {
                    'p': {'x': 1, 'y': 2}, 
                    'factor': 3,
                },
            },
        )

        assert response.json()['result'] == {'x': 3, 'y': 6}

    The constructor has two required parameters:

    1. [A client from the jsonrpcclient library](https://jsonrpcclient.readthedocs.io/en/latest/examples.html)
        for your desired transport.
        As a convenience, you can also just pass a string representing a URL,
        which will be used to construct an HTTPClient.
    2. An object defining your methods.
        The method body can be empty, InstantClient just uses the signature and type hints
        to serialize the arguments and deserialize the result
        with the help of [datafunctions](https://github.com/alexmojaki/datafunctions).

    The `methods` attribute of the client is a simple proxy so that this:

        client.methods.scale(Point(1, 2), factor=3)

    is equivalent to:

        client.request("scale", Point(1, 2), factor=3)

    which in turn looks up the signature of the original method. 
    """
    def __init__(self, url_or_client: Union[str, Client], methods: T):
        self.client: Client
        if isinstance(url_or_client, str):
            self.client = HTTPClient(url_or_client)
        else:
            self.client = url_or_client

        self.methods = self._original_methods = methods

        client_self = self

        class MethodsProxy:
            def __getattr__(self, method_name):
                return partial(client_self.request, method_name)

        # Replace self.methods with the proxy and hope that
        # static analysers don't notice
        setattr(self, "methods"[::-1][::-1], MethodsProxy())

    def request(self, method_name, *args, **kwargs):
        method = getattr(self._original_methods, method_name)
        method = datafunction(method)

        # Here we use datafunction in reverse
        data = method.dump_arguments(*args, **kwargs)
        response = self.client.request(method_name, **data)
        return method.load_result(response.data.result)
