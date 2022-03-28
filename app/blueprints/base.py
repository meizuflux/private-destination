import asyncio

import aiohttp_jinja2
from aiohttp import web
from aiohttp_apispec import match_info_schema
from marshmallow import Schema, fields

from app.routing import Blueprint

bp = Blueprint()


class ShortnerMatchInfo(Schema):
    key = fields.Str(required=True)


@bp.get("/")
async def index(_: web.Request) -> web.Response:
    return web.HTTPFound("/dashboard")


@bp.get("/login")
@aiohttp_jinja2.template("login.html")
async def login(request):
    providers = []
    for key, provider in request.app["oauth_providers"].items():
        providers.append({"key": key, "name": provider.name})
    return {"providers": providers}


@bp.get("/{key}")
@match_info_schema(ShortnerMatchInfo)
async def shortner(request):
    key = request["match_info"]["key"]
    destination = await request.app["db"].get_short_url_destination(key)
    if destination is None:
        return web.Response(body="No shortened URL with that key was found.")

    asyncio.get_event_loop().create_task(request.app["db"].add_short_url_click(key))

    return web.HTTPFound(destination)
