import asyncio

import aiohttp_jinja2
from aiohttp import web
from aiohttp_apispec import match_info_schema

from app.models.shortener import ShortenerAliasSchema
from app.routing import Blueprint
from app.utils.auth import verify_user
from app.utils.db import add_short_url_click, select_short_url_destination

bp = Blueprint()


@bp.get("/")
async def login(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None, needs_authorization=True) is True:
        return web.HTTPFound("/dashboard")

    return await aiohttp_jinja2.render_template_async("index.html", request, {})


@bp.get("/{alias}")
@match_info_schema(ShortenerAliasSchema)
async def shortener(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]
    destination = await select_short_url_destination(request.app["db"], alias=alias)
    if destination is None:
        return web.Response(body="No shortened URL with that alias was found.")  # TODO: make a view for this

    # run in background so that user can go to destination faster
    asyncio.get_event_loop().create_task(add_short_url_click(request.app["db"], alias=alias))

    return web.HTTPFound(destination)
