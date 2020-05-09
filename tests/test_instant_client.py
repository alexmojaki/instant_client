from dataclasses import dataclass
from typing import Any

import jsonrpcclient.client
from datafunctions import ArgumentError
from flask import Flask
from instant_api import InstantAPI
from jsonrpcclient import Response
from jsonrpcclient.clients.http_client import HTTPClient

from instant_client import InstantClient
from .utils import raises_with_cause

app = Flask(__name__)


@dataclass
class Point:
    x: int
    y: int


@InstantAPI(app)
class Methods:
    def translate(self, p: Point, dx: int, dy: int) -> Point:
        """
        Move a point by dx and dy.
        Other stuff here doesn't go into swagger.
        """
        return Point(p.x + dx, p.y + dy)


app.config['TESTING'] = True
flask_client = app.test_client()


class _TestJsonRpcClient(jsonrpcclient.client.Client):
    def __init__(self, test_client, endpoint):
        super().__init__()
        self.test_client = test_client
        self.endpoint = endpoint

    def send_message(
            self, request: str, response_expected: bool, **kwargs: Any
    ) -> Response:
        response = self.test_client.post(self.endpoint, data=request.encode())
        return Response(response.data.decode("utf8"), raw=response)


rpc_client = _TestJsonRpcClient(flask_client, "/api/")
client_methods = InstantClient(rpc_client, Methods()).methods


def test_simple():
    for methods in [
        client_methods,
        InstantClient(_TestJsonRpcClient(flask_client, "/api/translate"), Methods()).methods,
        Methods(),
    ]:
        assert methods.translate(Point(1, 2), 3, 4) == Point(4, 6)


def test_client_argument_error():
    with raises_with_cause(ArgumentError, TypeError, "missing a required argument: 'dy'"):
        client_methods.translate(1, 3)


def test_url_as_client():
    client = InstantClient("url", None)
    assert isinstance(client.client, HTTPClient)
    assert client.client.endpoint == "url"
