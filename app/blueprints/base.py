import asyncio

import aiohttp_jinja2
import psutil
from aiohttp import web
from aiohttp_apispec import match_info_schema

from app.models.shortener import ShortenerAliasSchema
from app.routing import Blueprint
from app.utils.auth import requires_auth, verify_user
from app.utils.db import (
    add_short_url_click,
    select_short_url_destination,
    select_short_urls_count,
    select_notes_count,
    select_total_notes_count,
    select_total_sessions_count,
    select_total_short_urls_count,
    select_total_users_count,
)

bp = Blueprint(name="base")


@bp.get("/", name="index")
async def login(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    return await aiohttp_jinja2.render_template_async("index.html.jinja", request, {})


@bp.get("/dashboard", name="dashboard")
@requires_auth(redirect=True, scopes=["id", "admin"])
@aiohttp_jinja2.template("dashboard/index.html.jinja")
async def index(request: web.Request):
    async with request.app["db"].acquire() as conn:
        url_count = await select_short_urls_count(conn, owner=request["user"]["id"])
        notes_count = await select_notes_count(conn, owner=request["user"]["id"])
    return {"url_count": url_count, "notes_count": notes_count}


@bp.get("/admin", name="admin")
@aiohttp_jinja2.template("admin/index.html.jinja")
async def home(request: web.Request):
    async with request.app["db"].acquire() as conn:
        urls_count = await select_total_short_urls_count(conn)
        users_count = await select_total_users_count(conn)
        sessions_count = await select_total_sessions_count(conn)
        notes_count = await select_total_notes_count(conn)

    return {
        "counters": {"urls": urls_count, "users": users_count, "sessions": sessions_count, "notes": notes_count},
        "stats": {"cpu_percent": psutil.cpu_percent(), "memory_percent": psutil.virtual_memory()[2]},
    }


@bp.get("/{alias}", name="shortener")
@match_info_schema(ShortenerAliasSchema)
async def shortener(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]
    destination = await select_short_url_destination(request.app["db"], alias=alias)
    if destination is None:
        return web.Response(body="No shortened URL with that alias was found.")  # TODO: make a view for this

    # run in background so that user can go to destination faster
    asyncio.get_event_loop().create_task(add_short_url_click(request.app["db"], alias=alias))

    return web.HTTPFound(destination)
