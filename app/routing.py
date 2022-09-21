"""Module for custom routing"""
from __future__ import annotations

from typing import Any, Iterable, List

from aiohttp import hdrs, web
from aiohttp.web_routedef import AbstractRouteDef, RouteDef, _Deco, _HandlerType


class Blueprint:
    def __init__(
        self, prefix: str = "", *, name: str = None, subblueprints: Iterable[Blueprint] = []
    ) -> None:  # pylint: disable=dangerous-default-value
        self.__prefix: str = prefix
        self.__name = name
        self.__route_table = web.RouteTableDef()
        for blueprint in subblueprints:
            self.__route_table._items.extend(blueprint.routes)

    def add_subblueprint(self, blueprint: Blueprint) -> None:
        """Add a subblueprint"""
        self.__route_table._items.extend(blueprint.routes)  # pylint: disable=protected-access

    @property
    def prefix(self) -> str:
        """Route prefix"""
        return self.__prefix

    @property
    def name(self) -> str | None:
        """Name of blueprint"""
        return self.__name

    @property
    def route_table(self) -> web.RouteTableDef:
        """Route table"""
        return self.__route_table

    @property
    def routes(self) -> List[AbstractRouteDef]:
        """Route table items"""
        return self.__route_table._items  # pylint: disable=protected-access

    def route(self, path: str, *, methods: List[str], **kwargs: Any) -> _Deco:
        """Add a route"""

        def decorator(handler: _HandlerType) -> _HandlerType:
            # name = kwargs.get("name")
            # if name is None:
            # kwargs["name"] = handler.__name__

            if self.__name is not None:
                name = kwargs.get("name")
                if name is not None:
                    if not name.startswith(self.__name):
                        kwargs["name"] = f"{self.__name}.{name}"

            for method in methods:
                self.__route_table._items.append(  # pylint: disable=protected-access
                    RouteDef(method, self.__prefix + path, handler, kwargs)
                )  # pylint: disable=protected-access
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


def url_for(app: web.Application, name: str, *, query: dict[str, str] = None, **match_info: str | int) -> str:
    """Finds the url for a named route"""
    resource = app.router.get(name)

    if resource is None:
        raise RuntimeError(f"No route with name {name} found")

    parts = {k: str(v) for k, v in match_info.items()}

    _url = resource.url_for(**parts)
    if query:
        _url = _url.with_query(query)
    url = str(_url)

    return url
