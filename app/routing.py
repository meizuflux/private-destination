from typing import Any, List

from aiohttp import hdrs, web
from aiohttp.web_routedef import RouteDef, _Deco, _HandlerType


class Blueprint(web.RouteTableDef):
    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        assert not prefix.endswith("/"), "Prefix cannot end with a slash"
        super().__init__()

    def route(self, path: str, *, methods: List[str], **kwargs: Any) -> _Deco:
        def inner(handler: _HandlerType) -> _HandlerType:
            for method in methods:
                self._items.append(RouteDef(method, self._prefix + path, handler, kwargs))
            return handler

        return inner

    def head(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(path, methods=[hdrs.METH_HEAD], **kwargs)

    def get(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(path, methods=[hdrs.METH_GET], **kwargs)

    def post(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(path, methods=[hdrs.METH_POST], **kwargs)

    def put(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(path, methods=[hdrs.METH_PUT], **kwargs)

    def patch(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(path, methods=[hdrs.METH_PATCH], **kwargs)

    def delete(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(path, methods=[hdrs.METH_DELETE], **kwargs)
