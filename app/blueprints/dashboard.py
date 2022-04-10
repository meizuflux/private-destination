from io import BytesIO
from json import dumps
from math import ceil

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from aiohttp_jinja2 import render_template_async, template
from asyncpg import UniqueViolationError
from marshmallow import ValidationError
from multidict import MultiDict, MultiDictProxy

from app.utils.shortener import generate_url_alias
from app.models.auth import (
    SessionSchema,
    UserIDSchema,
    UsersEditSchema,
    UsersFilterSchema,
)
from app.models.shortener import (
    ShortenerAliasSchema,
    ShortenerCreateSchema,
    ShortenerEditSchema,
    ShortenerFilterSchema,
)
from app.routing import Blueprint
from app.utils import Status
from app.utils.auth import create_user, edit_user, generate_api_key, requires_auth
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
    update_api_key,
    update_short_url,
    update_user,
)
from app.utils.forms import parser

bp = Blueprint("/dashboard")

# these all need the 'admin' scope for the sidebar "Manage Users" to show up
@bp.get("")
@requires_auth(redirect=True, scopes=["id", "admin"], needs_authorization=False)
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
                    "alias_error": e.messages.get("alias"),
                    "url_error": e.messages.get("destination"),
                    "domain": f"https://{request.app['config']['domain']}/",
                    "alias": e.data.get("alias"),
                    "destination": e.data.get("destination"),
                },
                status=400,
            )

        alias = args.get("alias")
        if alias is None or alias == "":
            alias = await generate_url_alias(request.app["db"])
        destination = args.get("destination")

        try:
            await insert_short_url(request.app["db"], owner=request["user"]["id"], alias=alias, destination=destination)
        except UniqueViolationError:
            return await render_template_async(
                "dashboard/shortener/create.html",
                request,
                {
                    "alias_error": ["A shortened URL with this alias already exists"],
                    "domain": f"https://{request.app['config']['domain']}/",
                    "alias": alias,
                    "destination": destination,
                },
                status=400,
            )

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/create.html", request, {"domain": f"https://{request.app['config']['domain']}/"}
    )


@bp.get("/shortener/{alias}/edit")
@bp.post("/shortener/{alias}/edit")
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(ShortenerAliasSchema())
async def edit_short_url_(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]

    short_url = await select_short_url(request.app["db"], alias=alias)
    if short_url is None:
        return await render_template_async(
            "dashboard/shortener/edit.html",
            request,
            {
                "error": {
                    "title": "Unknown Short URL",
                    "message": f"Could not locate short URL"
                },
                "domain": f"https://{request.app['config']['domain']}/",
            },
        )

    if short_url["owner"] != request["user"]["id"]:
        return await render_template_async(
            "dashboard/shortener/edit.html",
            request,
            {
                "error": {
                    "title": "Missing Permissions",
                    "message": f"You aren't the owner of this short URL"
                },
                "domain": f"https://{request.app['config']['domain']}/",
            },
        )

    if request.method == "POST":
        try:
            args = await parser.parse(ShortenerEditSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/shortener/edit.html",
                request,
                {
                    "alias_error": e.messages.get("alias"),
                    "destination_error": e.messages.get("destination"),
                    "domain": f"https://{request.app['config']['domain']}/",
                    "alias": e.data.get("alias"),
                    "destination": e.data.get("destination"),
                },
                status=400,
            )

        new_alias = args.get("alias")
        if new_alias is None or new_alias == "":
            new_alias = await generate_url_alias(request.app["db"])
        destination = args["destination"]

        try:
            await update_short_url(
                request.app["db"],
                alias=alias,
                new_alias=new_alias,
                destination=destination,
                reset_clicks=args.get("reset_clicks", False),
            )
        except UniqueViolationError as e:
            return await render_template_async(
                "dashboard/shortener/edit.html",
                request,
                {
                    "alias_error": ["A shortened URL with this alias already exists"],
                    "alias": new_alias,
                    "destination": destination,
                    "clicks": None,
                    "domain": f"https://{request.app['config']['domain']}/",

                },
                status=400,
            )

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/edit.html",
        request,
        {
            "alias": short_url["alias"],
            "destination": short_url["destination"],
            "clicks": short_url["clicks"],
            "domain": f"https://{request.app['config']['domain']}/",
        },
    )


@bp.get("/shortener/{alias}/delete")
@bp.post("/shortener/{alias}/delete")
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(ShortenerAliasSchema)
async def delete_short_url_(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]

    short_url = await select_short_url(request.app["db"], alias=alias)
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
        await delete_short_url(request.app["db"], alias=alias)

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/delete.html",
        request,
        {"alias": short_url["alias"], "destination": short_url["destination"], "clicks": short_url["clicks"]},
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
        "URL": "https://mzf.one/$json:alias$",
        "ErrorMessage": "$json:message$",
    }

    return web.Response(
        body=BytesIO(dumps(data).encode("utf-8")).getbuffer(),
        headers={"Content-Disposition": 'attachment; filename="mzf.one.sxcu"'},
    )


@bp.get("/settings")
@bp.get("/settings/account")
@template("dashboard/settings/account.html")
@requires_auth(redirect=True, scopes=["id", "api_key", "admin"], needs_authorization=False)
async def account_settings(request: web.Request):
    user = await select_user(request.app["db"], user_id=request["user"]["id"])

    return {
        "id": user["id"],
        "email": user["email"],
        "authorized": user["authorized"],
        "admin": user["admin"],
        "joined": user["joined"],
    }


@bp.get("/settings/api_key")
@requires_auth(redirect=False, scopes=["api_key", "admin"])
@template("dashboard/settings/api_key/index.html")
async def api_key_settings(_: web.Request):
    return {}


@bp.get("/settings/api_key/regenerate")
@bp.post("/settings/api_key/regenerate")
@requires_auth(redirect=False, scopes=["id", "api_key", "admin"])
async def regen_api_key(request: web.Request) -> web.Response:
    if request.method == "POST":
        async with request.app["db"].acquire() as conn:
            await update_api_key(request.app["db"], user_id=request["user"]["id"], api_key=await generate_api_key(conn))

        return web.HTTPFound("/dashboard/settings/api_key")

    return await render_template_async("/dashboard/settings/api_key/regen.html", request, {})


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

@bp.get("/settings/account/edit")
@bp.post("/settings/account/edit")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def edit_self(request: web.Request):
    user = await select_user(request.app["db"], user_id=request["user"]["id"])

    if request.method == "POST":
        form = await request.post()

        # user edit schema requires the authorized field but the edit self doesn't have it
        # and injecting it into the template is dangerous (the user could edit the html)
        # so this way we can just inject the user's current value by overriding the form values
        # also a note: request.post is supposed to be async that's why the override is async
        async def inject_authorized():
            return MultiDict(
            {
                "email": form["email"],
                "authorized": user["authorized"],
            }
        )
        request.post = inject_authorized
        status, ret = await edit_user(
            request,
            old_user=user,
            template="dashboard/settings/edit.html",
        )
        if status is Status.ERROR:
            return ret

        return web.HTTPFound("/dashboard/settings")

    return await render_template_async(
        "dashboard/settings/edit.html",
        request,
        {
            "id": user["id"],
            "email": user["email"],
            "authorized": user["authorized"],
            "admin": user["admin"],
            "joined": user["joined"],
        },
    )

@bp.get("/settings/account/delete")
@bp.post("/settings/account/delete")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def edit_self(request: web.Request):
    if request.method == "POST":
        await delete_user(request.app["db"], user_id=request["user"]["id"])


        res = web.HTTPFound("/")
        res.del_cookie("_session")
        return res

    return await render_template_async(
        "dashboard/settings/delete.html",
        request,
        {},
    )


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
@requires_auth(admin=True, redirect=True, scopes="id", needs_authorization=False)
async def edit_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]
    user = await select_user(request.app["db"], user_id=user_id)
    is_self = user_id == request["user"]["id"]

    if user is None:
        return await render_template_async(
            "dashboard/users/edit.html",
            request,
            {"error": {"title": "Unknown User", "message": "Could not locate user"}},
            status=404,
        )

    if request.method == "POST":
        status, ret = await edit_user(
            request,
            old_user=user,
            template="dashboard/users/edit.html",
            extra_ctx={
                "is_self": is_self,
            }
        )
        if status is Status.ERROR:
            return ret

        return web.HTTPFound("/dashboard/users")

    return await render_template_async(
        "dashboard/users/edit.html",
        request,
        {
            "id": user["id"],
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

    if user is None:
        return await render_template_async(
            "dashboard/users/delete.html",
            request,
            {"error": {"title": "Unknown User", "message": "Could not locate user"}},
            status=404,
        )

    if request.method == "POST":
        await delete_user(request.app["db"], user_id=user_id)

        return web.HTTPFound("/dashboard/users")

    return await render_template_async(
        "dashboard/users/delete.html",
        request,
        {"id": user["id"], "email": user["email"]},
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
