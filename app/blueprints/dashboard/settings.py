from aiohttp_apispec import match_info_schema
from aiohttp_jinja2 import render_template_async, template
from multidict import MultiDict
from app.models.auth import SessionSchema
from app.routing import Blueprint
from app.utils import Status

from app.utils.auth import edit_user, generate_api_key, requires_auth
from app.utils.db import delete_session, delete_user, select_sessions, select_user, update_api_key
from aiohttp import web


bp = Blueprint("/dashboard/settings")

@bp.get("")
@bp.get("/account")
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


@bp.get("/api_key")
@requires_auth(redirect=False, scopes=["api_key", "admin"])
@template("dashboard/settings/api_key/index.html")
async def api_key_settings(_: web.Request):
    return {}


@bp.get("/api_key/regenerate")
@bp.post("/api_key/regenerate")
@requires_auth(redirect=False, scopes=["id", "api_key", "admin"])
async def regen_api_key(request: web.Request) -> web.Response:
    if request.method == "POST":
        async with request.app["db"].acquire() as conn:
            await update_api_key(request.app["db"], user_id=request["user"]["id"], api_key=await generate_api_key(conn))

        return web.HTTPFound("/dashboard/settings/api_key")

    return await render_template_async("/dashboard/settings/api_key/regen.html", request, {})


@bp.get("/sessions")
@template("dashboard/settings/sessions.html")
@requires_auth(redirect=True, scopes=["id", "admin"], needs_authorization=False)
async def sessions_settings(request: web.Request):
    user_sessions = await select_sessions(request.app["db"], user_id=request["user"]["id"])
    return {"sessions": user_sessions, "current_session": request.cookies.get("_session")}


@bp.post("/sessions/{token}/delete")
@requires_auth(redirect=True, scopes=["id"], needs_authorization=False)
@match_info_schema(SessionSchema)
async def delete_session_(request: web.Request) -> web.Response:
    # we don't need to check ownership since there is an extremely low chance of two uuids ever being the same (ie can't be guessed)
    await delete_session(request.app["db"], token=request["match_info"]["token"])
    return web.HTTPFound("/dashboard/settings/sessions")


@bp.get("/shortener")
@template("dashboard/settings/shortener.html")
@requires_auth(redirect=True, scopes="admin")
async def shortener_settings(_: web.Request):
    return {}

@bp.get("/account/edit")
@bp.post("/account/edit")
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

@bp.get("/account/delete")
@bp.post("/account/delete")
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