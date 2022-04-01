from importlib.metadata import requires
from io import BytesIO
from json import dumps
from math import ceil

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from aiohttp_jinja2 import render_template_async, template
from asyncpg import UniqueViolationError
from marshmallow import Schema, ValidationError, fields, validate

from app.blueprints.api.shortner import CreateUrlSchema, generate_url_key
from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.db import (
    delete_short_url,
    insert_short_url,
    select_sessions,
    select_short_url,
    select_short_url_count,
    select_short_urls,
    select_users,
    update_short_url,
)
from app.utils.forms import parser


class ShortnerQuerystring(Schema):
    page = fields.Integer(validate=validate.Range(min=1, error="Page must be greater than or equal to 1"))
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"key", "destination", "clicks", "creation_date"}))


class UsersQuerystring(Schema):
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"username", "id", "authorized", "email", "joined"}))

class KeySchema(Schema):
    key = fields.String(required=True)

class EditUrlSchema(Schema):
    key = fields.String()
    destination = fields.URL(required=True)
    reset_clicks = fields.Boolean()


bp = Blueprint("/dashboard")

# these all need the 'admin' scope for the sidebar "Manage Users" to show


@bp.get("")
@requires_auth(redirect=True, scopes=["id", "username", "admin"])
@template("dashboard/index.html")
async def index(request: web.Request) -> web.Response:
    url_count = await select_short_url_count(request.app["db"], owner=request["user"]["id"])
    return {"url_count": url_count}


@bp.get("/shortner")
@requires_auth(redirect=True, scopes=["id", "admin"])
@querystring_schema(ShortnerQuerystring)
@template("dashboard/shortner/index.html")
async def shortner(request: web.Request) -> web.Response:
    current_page = request["querystring"].get("page", 1) - 1
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
        urls_count = await select_short_url_count(conn, owner=request["user"]["id"])

    max_pages = ceil(urls_count / 50)

    if max_pages == 0:
        max_pages = 1
    return {
        "current_page": current_page + 1,
        "max_pages": max_pages,
        "values": urls,
        "sortby": sortby,
        "direction": direction,
    }


@bp.get("/shortner/create")
@bp.post("/shortner/create")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def create_short_url_(request: web.Request) -> web.Response:
    if request.method == "POST":
        try:
            args = await parser.parse(CreateUrlSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/shortner/create.html",
                request,
                {
                    "key_error": e.messages.get("key"),
                    "url_error": e.messages.get("destination"),
                },
                status=400,
            )

        key = args.get("key")
        if key is None or key == "":
            key = await generate_url_key(request.app["db"])
        destination = args.get("destination")

        try:
            await insert_short_url(request.app["db"], owner=request["user"]["id"], key=key, destination=destination)
        except UniqueViolationError:
            return await render_template_async(
                "dashboard/shortner/create.html",
                request,
                {
                    "key_error": ["A shortened URL with this key already exists"],
                },
                status=400,
            )

        return web.HTTPFound("/dashboard/shortner")

    return await render_template_async("dashboard/shortner/create.html", request, {})

@bp.get("/shortner/{key}/edit")
@bp.post("/shortner/{key}/edit")
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(KeySchema)
async def edit_short_url_(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]

    short_url = await select_short_url(
        request.app["db"],
        key=key
    )
    if short_url is None:
        return await render_template_async(
            "dashboard/shortner/edit.html",
            request,
            {"error": {
                "title": "Unknown Short URL",
                "message": f"Could not locate short URL" 
            }}
        )

    if short_url["owner"] != request["user"]["id"]:
        return await render_template_async(
            "dashboard/shortner/edit.html",
            request,
            {"error": {
                "title": "Missing Permissions",
                "message": f"You aren't the owner of this short URL" 
            }}
        )
    
    if request.method == "POST":
        try:
            args = await parser.parse(EditUrlSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/shortner/edit.html",
                request,
                {
                    "key_error": e.messages.get("key"),
                    "destination_error": e.messages.get("destination"),
                },
                status=400,
            )

        new_key = args.get("key")
        if new_key is None or new_key == "":
            new_key = await generate_url_key(request.app["db"])
        destination = args["destination"]

        try:
            await update_short_url(
                request.app["db"],
                key=key,
                new_key=new_key,
                destination=destination,
                reset_clicks=args.get("reset_clicks", False)
            )
        except UniqueViolationError as e:
            return await render_template_async(
                "dashboard/shortner/edit.html",
                request,
                {
                    "key_error": ["A shortened URL with this key already exists"],
                    "key": new_key,
                    "destination": destination,
                    "clicks": None
                },
                status=400
            )

        return web.HTTPFound("/dashboard/shortner")

    return await render_template_async("dashboard/shortner/edit.html", request, {
        "key": short_url["key"],
        "destination": short_url["destination"],
        "clicks": short_url["clicks"]
    })

@bp.get("/shortner/{key}/delete")
@bp.post("/shortner/{key}/delete")
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(KeySchema)
async def edit_short_url_(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]

    short_url = await select_short_url(
        request.app["db"],
        key=key
    )
    if short_url is None:
        return await render_template_async(
            "dashboard/shortner/delete.html",
            request,
            {"error": {
                "title": "Unknown Short URL",
                "message": f"Could not locate short URL" 
            }}
        )

    if short_url["owner"] != request["user"]["id"]:
        return await render_template_async(
            "dashboard/shortner/delete.html",
            request,
            {"error": {
                "title": "Missing Permissions",
                "message": f"You aren't the owner of this short URL" 
            }}
        )

    if request.method == "POST":
        await delete_short_url(
            request.app["db"],
            key=key
        )

        return web.HTTPFound("/dashboard/shortner")


    return await render_template_async("dashboard/shortner/delete.html", request, {
        "key": short_url["key"],
        "destination": short_url["destination"],
        "clicks": short_url["clicks"]
    })


@bp.get("/shortner/sharex")
@requires_auth(redirect=False, scopes=["api_key"])
async def sharex_config(request: web.Request) -> web.Response:
    data = {
        "Version": "13.4.0",
        "DestinationType": "URLShortener",
        "RequestMethod": "POST",
        "RequestURL": "https://mzf.one/api/shortner",
        "Headers": {"x-api-key": request["user"]["api_key"]},
        "Body": "JSON",
        "Data": '{"destination":"$input$"}',
        "URL": "https://mzf.one/$json:key$",
        "ErrorMessage": "$json:message$",
    }

    return web.Response(
        body=BytesIO(dumps(data).encode("utf-8")).getbuffer(),
        headers={"Content-Disposition": 'attachment; filename="mzf.one.sxcu"'},
    )


@bp.get("/settings")
@template("dashboard/settings/index.html")
@requires_auth(redirect=True, scopes=["api_key", "username", "admin"])
async def general_settings(_: web.Request) -> web.Response:
    return {}


@bp.get("/settings/sessions")
@template("dashboard/settings/sessions.html")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def sessions_settings(request: web.Request) -> web.Response:
    user_sessions = await select_sessions(request.app["db"], user_id=request["user"]["id"])
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

    users = await select_users(request.app["db"], sortby=sortby, direction=direction)
    return {"users": users, "sortby": sortby, "direction": direction}
