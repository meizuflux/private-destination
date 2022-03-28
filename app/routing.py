from typing import Any

from aiohttp import web
from aiohttp.web_routedef import _Deco


class Blueprint(web.RouteTableDef):
    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        assert not prefix.endswith("/"), "Prefix cannot end with a slash"
        super().__init__()

    def route(self, method: str, path: str, **kwargs: Any) -> _Deco:

        return super().route(method, self._prefix + path, **kwargs)
