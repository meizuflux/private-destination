import aiohttp_jinja2
from aiohttp import web
from aiohttp_apispec import querystring_schema
from marshmallow import Schema, fields, validate

from app.routing import Blueprint
from app.utils.auth import requires_auth


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
@aiohttp_jinja2.template("dashboard/dashboard.html")
async def index(request: web.Request) -> web.Response:
    urls = await request.app["db"].get_short_url_count(request["user"]["id"])
    return {"url_count": urls}


@bp.get("/shortner")
@requires_auth(redirect=True, scopes=["id", "admin"])
@querystring_schema(ShortnerQuerystring)
@aiohttp_jinja2.template("dashboard/shortner.html")
async def shortner(request: web.Request) -> web.Response:
    current_page = request["querystring"].get("page", 1) - 1
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "creation_date")

    urls = await request.app["db"].get_short_urls(
        sortby=sortby.lower(),
        direction=direction.upper(),
        owner=request["user"]["id"],
        offset=current_page * 50,
    )
    max_pages = await request.app["db"].get_short_url_max_pages(request["user"]["id"])

    if max_pages == 0:
        max_pages = 1
    return {
        "current_page": current_page + 1,
        "max_pages": max_pages,
        "values": urls,
    }


@bp.get("/settings")
@aiohttp_jinja2.template("dashboard/settings.html")
@requires_auth(redirect=True, scopes=["api_key", "username", "admin"])
async def settings(_: web.Request) -> web.Response:
    return {}


@bp.get("/users")
@aiohttp_jinja2.template("dashboard/users.html")
@querystring_schema(UsersQuerystring)
@requires_auth(admin=True, redirect=True)
async def get(request: web.Request) -> web.Response:
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "joined")

    users = await request.app["db"].get_users(sortby, direction)
    return {"users": users}
