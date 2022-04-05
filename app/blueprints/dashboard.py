from io import BytesIO
from json import dumps
from math import ceil

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from aiohttp_jinja2 import render_template_async, template
from asyncpg import UniqueViolationError
from marshmallow import ValidationError

from app.blueprints.api.shortener import generate_url_key
from app.models.auth import (
    SessionSchema,
    UserIDSchema,
    UsersEditSchema,
    UsersFilterSchema,
)
from app.models.shortener import (
    ShortenerCreateSchema,
    ShortenerEditSchema,
    ShortenerFilterSchema,
    ShortenerKeySchema,
)
from app.routing import Blueprint
from app.utils import Status
from app.utils.auth import create_user, requires_auth
from app.utils.db import (
    delete_session,
    delete_short_url,
    delete_user,
    insert_short_url,
    select_sessions,
    select_short_url,
    select_short_url_count,
    select_short_urls,
    select_user,
    select_users,
    update_short_url,
    update_user,
)
from app.utils.forms import parser

bp = Blueprint("/dashboard")

# these all need the 'admin' scope for the sidebar "Manage Users" to show


@bp.get("")
@requires_auth(redirect=True, scopes=["id", "username", "admin"], needs_authorization=False)
@template("dashboard/index.html")
async def index(request: web.Request):
    url_count = await select_short_url_count(request.app["db"], owner=request["user"]["id"])
    return {"url_count": url_count}


@bp.get("/shortener")
@requires_auth(redirect=True, scopes=["id", "admin"])
@querystring_schema(ShortenerFilterSchema())
@template("dashboard/shortener/index.html")
async def shortener(request: web.Request):
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


@bp.get("/shortener/create")
@bp.post("/shortener/create")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def create_short_url_(request: web.Request) -> web.Response:
    if request.method == "POST":
        try:
            args = await parser.parse(ShortenerCreateSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/shortener/create.html",
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
                "dashboard/shortener/create.html",
                request,
                {
                    "key_error": ["A shortened URL with this key already exists"],
                },
                status=400,
            )

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async("dashboard/shortener/create.html", request, {})


@bp.get("/shortener/{key}/edit")
@bp.post("/shortener/{key}/edit")
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(ShortenerKeySchema())
async def edit_short_url_(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]

    short_url = await select_short_url(request.app["db"], key=key)
    if short_url is None:
        return await render_template_async(
            "dashboard/shortener/edit.html",
            request,
            {"error": {"title": "Unknown Short URL", "message": f"Could not locate short URL"}},
        )

    if short_url["owner"] != request["user"]["id"]:
        return await render_template_async(
            "dashboard/shortener/edit.html",
            request,
            {"error": {"title": "Missing Permissions", "message": f"You aren't the owner of this short URL"}},
        )

    if request.method == "POST":
        try:
            args = await parser.parse(ShortenerEditSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/shortener/edit.html",
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
                reset_clicks=args.get("reset_clicks", False),
            )
        except UniqueViolationError as e:
            return await render_template_async(
                "dashboard/shortener/edit.html",
                request,
                {
                    "key_error": ["A shortened URL with this key already exists"],
                    "key": new_key,
                    "destination": destination,
                    "clicks": None,
                },
                status=400,
            )

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/edit.html",
        request,
        {"key": short_url["key"], "destination": short_url["destination"], "clicks": short_url["clicks"]},
    )


@bp.get("/shortener/{key}/delete")
@bp.post("/shortener/{key}/delete")
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(ShortenerKeySchema)
async def delete_short_url_(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]

    short_url = await select_short_url(request.app["db"], key=key)
    if short_url is None:
        return await render_template_async(
            "dashboard/shortener/delete.html",
            request,
            {"error": {"title": "Unknown Short URL", "message": f"Could not locate short URL"}},
            status=404,
        )

    if short_url["owner"] != request["user"]["id"]:
        return await render_template_async(
            "dashboard/shortener/delete.html",
            request,
            {"error": {"title": "Missing Permissions", "message": f"You aren't the owner of this short URL"}},
            status=409,
        )

    if request.method == "POST":
        await delete_short_url(request.app["db"], key=key)

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/delete.html",
        request,
        {"key": short_url["key"], "destination": short_url["destination"], "clicks": short_url["clicks"]},
    )


@bp.get("/shortener/sharex")
@requires_auth(redirect=False, scopes=["api_key"])
async def shortener_sharex_config(request: web.Request) -> web.Response:
    data = {
        "Version": "13.4.0",
        "DestinationType": "URLShortener",
        "RequestMethod": "POST",
        "RequestURL": "https://mzf.one/api/shortener",
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
@requires_auth(redirect=True, scopes=["id", "api_key", "username", "admin"], needs_authorization=False)
async def general_settings(_: web.Request):
    return {}


@bp.get("/settings/sessions")
@template("dashboard/settings/sessions.html")
@requires_auth(redirect=True, scopes=["id", "admin"], needs_authorization=False)
async def sessions_settings(request: web.Request):
    user_sessions = await select_sessions(request.app["db"], user_id=request["user"]["id"])
    return {"sessions": user_sessions, "current_session": request.cookies.get("_session")}


@bp.post("/settings/sessions/{token}/delete")
@requires_auth(redirect=True, scopes=["id"], needs_authorization=False)
@match_info_schema(SessionSchema)
async def delete_session_(request: web.Request) -> web.Response:
    # we don't need to check ownership since there is an extremely low chance of two uuids ever being the same (ie can't be guessed)
    await delete_session(request.app["db"], token=request["match_info"]["token"])
    return web.HTTPFound("/dashboard/settings/sessions")


@bp.get("/settings/shortener")
@template("dashboard/settings/shortener.html")
@requires_auth(redirect=True, scopes="admin")
async def shortener_settings(_: web.Request):
    return {}


@bp.get("/users")
@template("dashboard/users/index.html")
@querystring_schema(UsersFilterSchema())
@requires_auth(admin=True, redirect=True)
async def users(request: web.Request):
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "joined")

    users = await select_users(request.app["db"], sortby=sortby, direction=direction)
    return {"users": users, "sortby": sortby, "direction": direction}


@bp.get("/users/{user_id}/edit")
@bp.post("/users/{user_id}/edit")
@match_info_schema(UserIDSchema)
@requires_auth(redirect=True, scopes=["id", "admin"], needs_authorization=False)
async def edit_user(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]
    user = await select_user(request.app["db"], user_id=user_id)
    is_self = user_id == request["user"]["id"]

    if is_self is False and request["user"]["admin"] is False:
        return await render_template_async(
            "dashboard/users/edit.html",
            request,
            {
                "error": {
                    "title": "Missing Permissions",
                    "message": "You need admin permissions to edit users other than yourself",
                },
            },
            status=409,
        )

    # this goes after the previous check since we don't want to reveal if the user id exists without checking first their admin perms
    if user is None:
        return await render_template_async(
            "dashboard/users/edit.html",
            request,
            {"error": {"title": "Unknown User", "message": f"Could not locate user"}},
            status=404,
        )

    if request.method == "POST":
        try:
            args = await parser.parse(UsersEditSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/users/edit.html",
                request,
                {
                    "username_error": e.messages.get("username"),
                    "email_error": e.messages.get("email"),
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "authorized": user["authorized"],
                    "admin": user["admin"],
                    "joined": user["joined"],
                    "is_self": is_self,
                },
                status=400,
            )

        try:
            await update_user(
                request.app["db"],
                user_id=user_id,
                username=args["username"],
                email=args["email"],
                authorized=args["authorized"],
            )
        except UniqueViolationError as e:
            return await render_template_async(
                "dashboard/users/edit.html",
                request,
                {
                    "email_error": ["A user with this email already exists"],
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "authorized": user["authorized"],
                    "admin": user["admin"],
                    "joined": user["joined"],
                    "is_self": is_self,
                },
                status=400,
            )

        return web.HTTPFound("/dashboard/users" if is_self is False else "/dashboard/settings")

    return await render_template_async(
        "dashboard/users/edit.html",
        request,
        {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "authorized": user["authorized"],
            "admin": user["admin"],
            "joined": user["joined"],
            "is_self": is_self,
        },
    )


@bp.get("/users/{user_id}/delete")
@bp.post("/users/{user_id}/delete")
@requires_auth(redirect=True, scopes=["id", "admin"], needs_authorization=False)
@match_info_schema(UserIDSchema)
async def delete_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]
    user = await select_user(request.app["db"], user_id=user_id)
    is_self = user_id == request["user"]["id"]

    if is_self is False and request["user"]["admin"] is False:
        return await render_template_async(
            "dashboard/users/delete.html",
            request,
            {
                "error": {
                    "title": "Missing Permissions",
                    "message": "You need admin permissions to edit users other than yourself",
                },
            },
            status=409,
        )

    # this goes after the previous check since we don't want to reveal if the user id exists without checking first their admin perms
    if user is None:
        return await render_template_async(
            "dashboard/users/delete.html",
            request,
            {"error": {"title": "Unknown User", "message": f"Could not locate user"}},
            status=404,
        )

    if request.method == "POST":
        await delete_user(request.app["db"], user_id=user_id)

        if is_self is True:
            res = web.HTTPFound("/")
            res.del_cookie("_session")
            return res
        return web.HTTPFound("/dashboard/users")

    return await render_template_async(
        "dashboard/users/delete.html",
        request,
        {"id": user["id"], "username": user["username"], "email": user["email"], "is_self": is_self},
    )


@bp.get("/users/create")
@bp.post("/users/create")
@requires_auth(admin=True, redirect=True)
async def create_user_(request: web.Request) -> web.Response:
    if request.method == "POST":
        status, ret = await create_user(request, template="onboarding.html", extra_ctx={"type": "signup"})
        if status is Status.ERROR:
            return ret

        return web.HTTPFound("/dashboard/users")

    return await render_template_async("dashboard/users/create.html", request, {})
