from typing import List

from aiohttp import web


def normalize_pattern(pattern: str):
    if pattern is None:
        return ""
    if pattern.startswith("/"):
        return pattern
    return "/" + pattern


def view(pattern=None):
    def decorator(fn):
        setattr(fn, "handler", True)
        setattr(fn, "pattern", normalize_pattern(pattern))
        return fn

    return decorator


class ControllerMeta(type):
    __views__ = []

    def __init__(cls, name, bases, attr_dict):
        super().__init__(name, bases, attr_dict)
        cls.__views__ = []

        for value in attr_dict.values():
            if hasattr(value, "handler"):
                cls.__views__.append(web.view(cls.class_name() + value.pattern, value))


class Controller(metaclass=ControllerMeta):
    __views__: List[web.RouteDef]

    def __init_subclass__(cls) -> None:
        views: List[web.RouteDef] = []
        for base in reversed(cls.__mro__):
            for member in base.__dict__.values():
                if hasattr(member, "handler"):
                    views.append(web.view(cls.class_name() + member.pattern, member))

        cls.__views__ = views

    @classmethod
    def add_routes(cls, app: web.Application):
        app.router.add_routes(cls.__views__)

    @classmethod
    def class_name(cls):
        return "/" + cls.__name__.lower()


class APIController(Controller):
    __views__: List[web.RouteDef]

    def __init_subclass__(cls) -> None:
        views: List[web.RouteDef] = []
        for base in reversed(cls.__mro__):
            for member in base.__dict__.values():
                if hasattr(member, "handler"):
                    views.append(web.view(cls.class_name() + member.pattern, member))

        cls.__views__ = views

    @classmethod
    def class_name(cls):
        return "/api/" + cls.__name__.lower()
