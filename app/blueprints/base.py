import asyncio

import aiohttp_jinja2
from aiohttp import web
from aiohttp_apispec import match_info_schema
from marshmallow import Schema, fields

from app.routing import Blueprint
from app.utils.auth import verify_user

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
    destination = await request.app["db"].get_short_url_destination(key)
    if destination is None:
        return web.Response(body="No shortened URL with that key was found.")

    asyncio.get_event_loop().create_task(request.app["db"].add_short_url_click(key))

    return web.HTTPFound(destination)
