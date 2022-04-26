"""Module for custom routing"""
from __future__ import annotations

from typing import Any, Iterable, List

from aiohttp import hdrs, web
from aiohttp.web_routedef import AbstractRouteDef, RouteDef, _Deco, _HandlerType

class Blueprint:
    def __init__(self, prefix: str = "", *, subblueprints: Iterable[Blueprint] = []): # pylint: disable=dangerous-default-value
        self.__prefix: str = prefix
        self.__route_table = web.RouteTableDef()
        for blueprint in subblueprints:
            self.__route_table._items.extend(blueprint.routes)

    def add_subblueprint(self, blueprint: Blueprint):
        """Add a subblueprint"""
        self.__route_table._items.extend(blueprint.routes) # pylint: disable=protected-access

    @property
    def prefix(self) -> str:
        """Route prefix"""
        return self.__prefix

    @property
    def route_table(self) -> web.RouteTableDef:
        """Route table"""
        return self.__route_table

    @property
    def routes(self) -> List[AbstractRouteDef]:
        """Route table items"""
        return self.__route_table._items # pylint: disable=protected-access

    def route(self, path: str, *, methods: List[str], **kwargs: Any) -> _Deco:
        """Add a route"""
        def decorator(handler: _HandlerType) -> _HandlerType:
            for method in methods:
                self.__route_table._items.append(RouteDef(method, self.__prefix + path, handler, kwargs)) # pylint: disable=protected-access
            return handler

        return decorator

    def head(self, path: str, **kwargs: Any) -> _Deco:
        """Add HEAD route"""
        return self.route(path, methods=[hdrs.METH_HEAD], **kwargs)

    def get(self, path: str, **kwargs: Any) -> _Deco:
        """Add GET route"""
        return self.route(path, methods=[hdrs.METH_GET], **kwargs)

    def post(self, path: str, **kwargs: Any) -> _Deco:
        """Add POST route"""
        return self.route(path, methods=[hdrs.METH_POST], **kwargs)

    def put(self, path: str, **kwargs: Any) -> _Deco:
        """Add PUT route"""
        return self.route(path, methods=[hdrs.METH_PUT], **kwargs)

    def patch(self, path: str, **kwargs: Any) -> _Deco:
        """Add PATCH route"""
        return self.route(path, methods=[hdrs.METH_PATCH], **kwargs)

    def delete(self, path: str, **kwargs: Any) -> _Deco:
        """Add DELETE route"""
        return self.route(path, methods=[hdrs.METH_DELETE], **kwargs)


def register_blueprint(app: web.Application, blueprint: Blueprint) -> None:
    """Register routes"""
    app.router.add_routes(blueprint.route_table)
