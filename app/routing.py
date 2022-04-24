"""Module for custom routing"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Iterable, Iterator, List, overload

from aiohttp import hdrs
from aiohttp.web_routedef import AbstractRouteDef, RouteDef, _Deco, _HandlerType


# source: https://github.com/aio-libs/aiohttp/blob/a0454809e3fd15f70c95d794addf005d9bd95b23/aiohttp/web_routedef.py#L154-L215
class Blueprint(Sequence[AbstractRouteDef]):
    """Container for routes"""

    def __init__(
        self, prefix: str = "", subblueprints: Iterable[Blueprint] = []
    ):  # pylint: disable=dangerous-default-value
        self.prefix: str = prefix
        self._items: List[AbstractRouteDef] = []
        for blueprint in subblueprints:
            for route in blueprint:
                self._items.append(route)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} count={len(self._items)}>"

    @overload
    def __getitem__(self, index: int) -> AbstractRouteDef:
        ...

    @overload
    def __getitem__(self, index: slice) -> List[AbstractRouteDef]:
        ...

    def __getitem__(self, index):
        return self._items[index]

    def __iter__(self) -> Iterator[AbstractRouteDef]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def route(self, path: str, *, methods: List[str], **kwargs: Any) -> _Deco:
        """Add a route"""

        def decorator(handler: _HandlerType) -> _HandlerType:
            for method in methods:
                self._items.append(RouteDef(method, self.prefix + path, handler, kwargs))
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
