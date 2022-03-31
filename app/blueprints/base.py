import asyncio
from io import BytesIO

import aiohttp_jinja2
from aiohttp import web
from aiohttp_apispec import match_info_schema
from marshmallow import Schema, fields

from app.routing import Blueprint
from app.utils.auth import verify_user
from app.utils.db import add_short_url_click, select_short_url_destination

bp = Blueprint()


class ShortnerMatchInfo(Schema):
    key = fields.Str(required=True)


@bp.get("/")
async def login(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    return await aiohttp_jinja2.render_template_async("index.html", request, {})

@bp.get("/{key}")
@match_info_schema(ShortnerMatchInfo)
async def shortner(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]
    destination = await select_short_url_destination(
        request.app["db"],
        key=key
    )
    if destination is None:
        return web.Response(body="No shortened URL with that key was found.")

    asyncio.get_event_loop().create_task(add_short_url_click(
        request.app["db"],
        key=key
    ))

    return web.HTTPFound(destination)
