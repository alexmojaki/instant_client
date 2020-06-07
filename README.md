# instant_client

[![Build Status](https://travis-ci.org/alexmojaki/instant_client.svg?branch=master)](https://travis-ci.org/alexmojaki/instant_client) [![Coverage Status](https://coveralls.io/repos/github/alexmojaki/instant_client/badge.svg?branch=master)](https://coveralls.io/github/alexmojaki/instant_client?branch=master) [![Supports Python versions 3.7+](https://img.shields.io/pypi/pyversions/instant_client.svg)](https://pypi.python.org/pypi/instant_client)

A type-safe [JSON-RPC](https://www.jsonrpc.org/) client with automatic (de)serialization. This makes it easy to use classes instead of raw dictionaries and allows your IDE or other tools to spot errors and give you assistance.

    pip install instant-client
    
For communication over HTTP (like in the example below):

    pip install 'instant-client[requests]'

`instant_client` can be used with any server implementing JSON-RPC, but it's best paired with [`instant_api`](https://github.com/alexmojaki/instant_api). For example, suppose the API server is set up like this:

```python
from dataclasses import dataclass
from flask import Flask
from instant_api import InstantAPI

app = Flask(__name__)

@dataclass
class Point:
    x: int
    y: int

@InstantAPI(app)
class Methods:
    def translate(self, p: Point, dx: int, dy: int) -> Point:
        return Point(p.x + dx, p.y + dy)

    def scale(self, p: Point, factor: int) -> Point:
        return Point(p.x * factor, p.y * factor)

if __name__ == '__main__':
    app.run()
```

Then using the client is as simple as:

```python
from server import Methods, Point  # the classes we defined above
from instant_client import InstantClient

# The type hint is a lie, but your linter/IDE doesn't know that!
methods: Methods = InstantClient("http://127.0.0.1:5000/api/", Methods()).methods

assert methods.scale(Point(1, 2), factor=3) == Point(3, 6)
```

That looks a lot like it just called `Methods.scale()` directly, which is the point (no pun intended), but under the hood it did in fact send an HTTP request to the server! The same code written more manually looks like this:

```python
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
```

In general, the `InstantClient` constructor has two required parameters:

1. [A client from the jsonrpcclient library](https://jsonrpcclient.readthedocs.io/en/latest/examples.html) for your desired transport. For example:

    ```python
    from jsonrpcclient.clients.zeromq_client import ZeroMQClient
    from instant_client import InstantClient
    
    client = InstantClient(ZeroMQClient("tcp://localhost:5000"), Methods())
    ```
    
    As a convenience, you can also just pass a string representing a URL, which will be used to construct an `HTTPClient`.

2. An object defining your methods. The method body can be empty, `InstantClient` just uses the signature and type hints to serialize the arguments and deserialize the result with the help of [datafunctions](https://github.com/alexmojaki/datafunctions).

The `methods` attribute of the client is a simple proxy so that this:

```python
client.methods.scale(Point(1, 2), factor=3)
```

is equivalent to:

```python
client.request("scale", Point(1, 2), factor=3)
```

which in turn looks up the signature of the original method. 

Your IDE/linter/type-checker should think that `client.methods` is the object you passed at the beginning, so you can get all the usual warnings and autocompletions. Adding your own type hint can help but shouldn't be necessary.
