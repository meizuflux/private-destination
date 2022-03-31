from importlib.metadata import requires
from io import BytesIO
from json import dumps
from aiohttp_jinja2 import template
from aiohttp import web
from aiohttp_apispec import querystring_schema
from app.utils.db import select_short_url_count, select_short_urls
from marshmallow import Schema, fields, validate

from app.routing import Blueprint
from app.utils.auth import requires_auth
from math import ceil


class ShortnerQuerystring(Schema):
    page = fields.Integer()
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"key", "destination", "clicks", "creation_date"}))


class UsersQuerystring(Schema):
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"username", "id", "authorized", "email", "joined"}))


bp = Blueprint("/dashboard")

# these all need the 'admin' scope for the sidebar "Manage Users" to show


@bp.get("")
@requires_auth(redirect=True, scopes=["id", "username", "admin"])
@template("dashboard/index.html")
async def index(request: web.Request) -> web.Response:
    urls = await request.app["db"].get_short_url_count(request["user"]["id"])
    return {"url_count": urls}


@bp.get("/shortner")
@requires_auth(redirect=True, scopes=["id", "admin"])
@querystring_schema(ShortnerQuerystring)
@template("dashboard/shortner.html")
async def shortner(request: web.Request) -> web.Response:
    current_page = abs(request["querystring"].get("page", 1) - 1) # needs to be positive
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "creation_date")

    async with request.app["db"].acquire() as conn:
        urls = await select_short_urls(
            conn,
            sortby=sortby,
            direction=direction.upper(),
            owner=request["user"]["id"],
            offset=current_page * 50,
        )
        urls_count = await select_short_url_count(
            conn,
            owner=request["user"]["id"]
        )

    max_pages = ceil(urls_count / 50)

    if max_pages == 0:
        max_pages = 1
    return {
        "current_page": current_page + 1,
        "max_pages": max_pages,
        "values": urls,
        "sortby": sortby,
        "direction": direction
    }

@bp.get("/shortner/sharex")
@requires_auth(redirect=False, scopes=["api_key"])
async def sharex_config(request: web.Request) -> web.Response:
    data = {
        "Version": "13.4.0",
        "DestinationType": "URLShortener",
        "RequestMethod": "POST",
        "RequestURL": "https://mzf.one/api/shortner",
        "Headers": {
            "x-api-key": request["user"]["api_key"]
        },
        "Body": "JSON",
        "Data": "{\n  \"destination\": \"$input$\"\n}",
        "URL": "https://mzf.one/$json:key$",
        "ErrorMessage": "$json:key$"
    }

    return web.Response(body=BytesIO(dumps(data).encode("utf-8")).getbuffer(), headers={"Content-Disposition": 'attachment; filename="mzf.one.sxcu"'})


@bp.get("/settings")
@template("dashboard/settings/index.html")
@requires_auth(redirect=True, scopes=["api_key", "username", "admin"])
async def general_settings(_: web.Request) -> web.Response:
    return {}

@bp.get("/settings/sessions")
@template("dashboard/settings/sessions.html")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def sessions_settings(request: web.Request) -> web.Response:
    user_sessions = await request.app["db"].fetch_sessions(request["user"]["id"])
    return {"sessions": user_sessions}

@bp.get("/settings/shortner")
@template("dashboard/settings/shortner.html")
@requires_auth(redirect=True, scopes="admin")
async def shortner_settings(_: web.Request) -> web.Response:
    return {}

@bp.get("/users")
@template("dashboard/users.html")
@querystring_schema(UsersQuerystring)
@requires_auth(admin=True, redirect=True)
async def get(request: web.Request) -> web.Response:
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "joined")

    users = await request.app["db"].get_users(sortby, direction)
    return {
        "users": users,
        "sortby": sortby,
        "direction": direction
    }
