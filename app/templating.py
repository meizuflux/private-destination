from collections.abc import Awaitable, Callable
from functools import cache
from typing import Any, Optional

import jinja2
from aiohttp import web

ContextProcessor = Callable[[web.Request], Awaitable[dict[str, Any]]]

TEMPLATE_SUFFIX = ".html.jinja"


@cache
def get_template_name(name: str) -> str:
    if not name.endswith(TEMPLATE_SUFFIX):
        return name + TEMPLATE_SUFFIX
    return name


async def request_processor(request: web.Request) -> dict[str, web.Request]:
    return {"request": request}


def setup(
    app: web.Application,
    *,
    loader: jinja2.FileSystemLoader | jinja2.PackageLoader = jinja2.FileSystemLoader("./templates"),
    global_functions: dict[str, Callable[[Any], Any]] = None,
    context_processors: list[ContextProcessor] = None,
    **options: Any,
) -> jinja2.Environment:
    env = jinja2.Environment(
        loader=loader, enable_async=True, autoescape=options.pop("autoescape", jinja2.select_autoescape()), **options
    )
    env.globals["app"] = app
    if global_functions:
        env.globals.update(global_functions)
    app["templating_environment"] = env
    if context_processors is None:
        context_processors = [request_processor]
    else:
        context_processors.append(request_processor)
    app["templating_context_processors"] = context_processors

    return env


async def get_context(request: web.Request, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if context is None:
        context = {}
    for processor in request.app["templating_context_processors"]:
        context.update(await processor(request))
    return context


async def render_template(
    template_name: str, request: web.Request, context: dict[str, Any] = None, status: int = 200
) -> web.Response:
    context = await get_context(request, context)
    template = request.app["templating_environment"].get_template(get_template_name(template_name))
    return web.Response(
        text=await template.render_async(context),
        status=status,
        content_type="text/html",
        charset="utf-8",
    )


async def render_string(source: str, request: web.Request, context: dict[str, Any], status: int = 200) -> web.Response:
    context = await get_context(request, context)
    template = request.app["templating_environment"].from_string(source)
    return web.Response(
        text=await template.render_async(context),
        status=status,
        content_type="text/html",
        charset="utf-8",
    )
