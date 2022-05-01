import asyncio

import psutil
from aiohttp import web
from aiohttp_apispec import match_info_schema

from app.models.shortener import ShortenerAliasSchema
from app.routing import Blueprint
from app.templating import render_template
from app.utils.auth import is_authorized, requires_auth, verify_user
from app.utils.db import (
    add_short_url_click,
    get_db,
    select_notes_count,
    select_short_url_destination,
    select_short_urls_count,
    select_total_notes_count,
    select_total_sessions_count,
    select_total_short_urls_count,
    select_total_users_count,
)

bp = Blueprint(name="base")


@bp.get("/", name="index")
async def login(request: web.Request) -> web.Response:
    if await is_authorized(request):
        return web.HTTPFound("/dashboard")

    return await render_template("index", request)


@bp.get("/dashboard", name="dashboard")
@requires_auth(scopes=["id", "admin"])
async def index(request: web.Request) -> web.Response:
    async with get_db(request).acquire() as conn:
        url_count = await select_short_urls_count(conn, owner=request["user"]["id"])
        notes_count = await select_notes_count(conn, owner=request["user"]["id"])
    return await render_template(
        "dashboard/index",
        request,
        {
            "url_count": url_count,
            "notes_count": notes_count,
        },
    )


@bp.get("/admin", name="admin")
async def home(request: web.Request) -> web.Response:
    async with get_db(request).acquire() as conn:
        urls_count = await select_total_short_urls_count(conn)
        users_count = await select_total_users_count(conn)
        sessions_count = await select_total_sessions_count(conn)
        notes_count = await select_total_notes_count(conn)
    return await render_template(
        "admin/index",
        request,
        {
            "counters": {"urls": urls_count, "users": users_count, "sessions": sessions_count, "notes": notes_count},
            "stats": {"cpu_percent": psutil.cpu_percent(), "memory_percent": psutil.virtual_memory()[2]},
        },
    )


@bp.get("/{alias}", name="shortener")
@match_info_schema(ShortenerAliasSchema)
async def shortener(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]
    destination = await select_short_url_destination(get_db(request), alias=alias)
    if destination is None:
        return web.Response(body="No shortened URL with that alias was found.")  # TODO: make a view for this

    # run in background so that user can go to destination faster
    asyncio.get_event_loop().create_task(add_short_url_click(get_db(request), alias=alias))

    return web.HTTPFound(destination)
