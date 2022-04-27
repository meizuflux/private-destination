from aiohttp import web
from aiohttp_apispec import match_info_schema
from aiohttp_jinja2 import render_template_async, template
from marshmallow import Schema, ValidationError, fields, validate
from multidict import MultiDict

from app.models.auth import SessionSchema
from app.routing import Blueprint
from app.utils import Status
from app.utils.auth import edit_user, generate_api_key, requires_auth
from app.utils.db import (
    delete_session,
    delete_user,
    select_notes_count,
    select_sessions,
    select_user,
    update_api_key,
)
from app.utils.forms import parser


def email_or_none(value: str):
    if value == "":
        return None
    try:
        return validate.Email()(value)
    except ValidationError:
        return None


class CreateInviteSchema(Schema):
    required_email = fields.String(validate=email_or_none)


bp = Blueprint("/dashboard/settings", name="settings")


@bp.get("/api_key", name="api_key")
@requires_auth(redirect=False, scopes=["api_key", "admin"])
@template("dashboard/settings/api_key/index.html.jinja")
async def api_key_settings(_: web.Request):
    return {}


@bp.route("/api_key/regenerate", methods=["GET", "POST"], name="regenerate_api_key")
@requires_auth(redirect=False, scopes=["id", "api_key", "admin"])
async def regen_api_key(request: web.Request) -> web.Response:
    if request.method == "POST":
        async with request.app["db"].acquire() as conn:
            await update_api_key(request.app["db"], user_id=request["user"]["id"], api_key=await generate_api_key(conn))

        return web.HTTPFound("/dashboard/settings/api_key")

    return await render_template_async("/dashboard/settings/api_key/regen.html.jinja", request, {})


@bp.get("/sessions", name="sessions")
@template("dashboard/settings/sessions.html.jinja")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def sessions_settings(request: web.Request):
    user_sessions = await select_sessions(request.app["db"], user_id=request["user"]["id"])
    return {"sessions": user_sessions, "current_session": request.cookies.get("_session")}


@bp.post("/sessions/{token}/delete", name="delete_session")
@requires_auth(redirect=True, scopes=["id"])
@match_info_schema(SessionSchema)
async def delete_session_(request: web.Request) -> web.Response:
    # we don't need to check ownership since there is an extremely low chance of two uuids ever being the same (ie can't be guessed)
    await delete_session(request.app["db"], token=request["match_info"]["token"])
    return web.HTTPFound("/dashboard/settings/sessions")


@bp.get("/shortener", name="shortener")
@template("dashboard/settings/shortener.html.jinja")
@requires_auth(redirect=True, scopes="admin")
async def shortener_settings(_: web.Request):
    return {}


@bp.route("/account/edit", methods=["GET", "POST"], name="edit_account")
@bp.route("", methods=["GET", "POST"], name="index")
@bp.route("/account", methods=["GET", "POST"], name="account_settings")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def edit_self(request: web.Request):
    user = await select_user(request.app["db"], user_id=request["user"]["id"])

    if request.method == "POST":
        ret = await edit_user(
            request,
            old_user=user,
            template="dashboard/settings/account.html.jinja",
        )
        if ret[0] is Status.ERROR:
            return ret[1]

        return web.HTTPFound("/dashboard/settings")

    return await render_template_async(
        "dashboard/settings/account.html.jinja",
        request,
        {
            "id": user["id"],
            "email": user["email"],
            "admin": user["admin"],
            "joined": user["joined"],
        },
    )


@bp.route("/account/delete", methods=["GET", "POST"], name="delete_account")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def delete_account(request: web.Request):
    if request.method == "POST":
        await delete_user(request.app["db"], user_id=request["user"]["id"])

        res = web.HTTPFound("/")
        res.del_cookie("_session")
        return res

    return await render_template_async(
        "dashboard/settings/delete.html.jinja",
        request,
        {},
    )


@bp.get("/invites", name="invites")
@requires_auth(redirect=True, scopes=["id", "admin"])
@template("dashboard/settings/invites.html.jinja")
async def invites_manager(request: web.Request):
    # sourcery skip: assign-if-exp, boolean-if-exp-identity, introduce-default-else, remove-unnecessary-cast
    invites = await request.app["db"].fetch(
        "SELECT code, used_by, required_email, creation_date FROM invites WHERE owner = $1 ORDER BY creation_date DESC",
        request["user"]["id"],
    )
    can_create = True
    if len(invites) > 5 and request["user"]["admin"] is False:
        can_create = False

    return {
        "invites": invites,
        "can_create": can_create,
    }


@bp.post("/invites", name="create_invite")
@requires_auth(redirect=True, scopes=["id", "admin"])
async def create_invite(request: web.Request) -> web.Response:
    # sourcery skip: assign-if-exp, boolean-if-exp-identity, introduce-default-else, remove-unnecessary-cast
    try:
        args = await parser.parse(CreateInviteSchema(), request, locations=["form"])
    except ValidationError as error:
        invites = await request.app["db"].fetch(
            "SELECT code, used_by, required_email, creation_date FROM invites WHERE owner = $1 ORDER BY creation_date DESC",
            request["user"]["id"],
        )
        can_create = True
        if len(invites) > 5 and request["user"]["admin"] is False:
            can_create = False
        return await render_template_async(
            "dashboard/settings/invites.html.jinja",
            request,
            {
                "email_error": error.messages.get("required_email"),
                "invites": invites,
                "can_create": can_create,
            },
            status=400,
        )

    async with request.app["db"].acquire() as conn:
        invites_count = await select_notes_count(conn, owner=request["user"]["id"])
        if invites_count > 5 and request["user"]["admin"] is False:
            return web.HTTPForbidden(reason="You can only create 5 invites")

        email = args["required_email"] if args["required_email"] != "" else None

        await conn.fetchval(
            "INSERT INTO invites (owner, required_email) VALUES ($1, $2) RETURNING code", request["user"]["id"], email
        )

    return web.HTTPFound("/dashboard/settings/invites")
