from uuid import UUID

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from marshmallow import Schema, ValidationError, fields
from passlib.hash import pbkdf2_sha512
from ua_parser import user_agent_parser

from app.models.auth import LoginSchema
from app.routing import Blueprint
from app.templating import render_template
from app.utils import Status
from app.utils.auth import create_user, requires_auth, verify_user
from app.utils.db import delete_session, get_db, insert_session
from app.utils.forms import parser


class InviteCodeSchema(Schema):
    code = fields.UUID()


async def login_user(request: web.Request, user_id: int, email: str, session_duration: int) -> web.Response:
    metadata = user_agent_parser.Parse(request.headers.getone("User-Agent"))
    browser = metadata["user_agent"]["family"]
    operating_system = metadata["os"]["family"]

    uuid = await insert_session(get_db(request), user_id=user_id, browser=browser, os=operating_system)

    res = web.HTTPFound("/dashboard")
    res.set_cookie(
        name="_session",
        value=str(uuid),
        max_age=session_duration,
        httponly=True,
        secure=not request.app["dev"],
        samesite="strict",  # using this lets me not need to setup csrf and whatnot
    )
    res.set_cookie(
        name="email",
        value=email,
        max_age=60 * 60 * 24 * 365,  # one year
        httponly=True,
        secure=not request.app["dev"],
        samesite="strict",
    )

    return res


bp = Blueprint("/auth", name="auth")


@bp.get("/invite/{code}", name="invite")
@match_info_schema(InviteCodeSchema())
async def invite(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None):
        return web.HTTPFound("/dashboard")
    return web.HTTPFound(f"/auth/login?code={request['match_info']['code']}")


@bp.route("/signup", methods=["GET", "POST"], name="signup")
@querystring_schema(InviteCodeSchema())
async def signup(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    invite_code = request["querystring"].get("code", "")

    if request.method == "POST":
        ret = await create_user(
            request, template="onboarding", extra_ctx={"type": "signup", "invite_code": invite_code}
        )
        if ret[0] is Status.ERROR:
            return ret[1]

        return await login_user(request, ret[1], ret[2], 86400)  # one day

    return await render_template("onboarding", request, {"type": "signup", "invite_code": invite_code})


@bp.route("/login", methods=["GET", "POST"], name="login")
async def login(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    if request.method == "POST":
        try:
            args = await parser.parse(LoginSchema(), request, locations=["form"])
        except ValidationError as error:
            messages = error.normalized_messages()
            return await render_template(
                "onboarding",
                request,
                {
                    "email_error": messages.get("email"),
                    "password_error": messages.get("password"),
                    "type": "login",
                    "email": error.data.get("email"),
                    "password": error.data.get("password"),
                },
                status=400,
            )

        row = await get_db(request).fetchrow(
            "SELECT id, password, session_duration FROM users WHERE email = $1", args["email"]
        )
        if row is None:
            return await render_template(
                "onboarding",
                request,
                {
                    "email_error": ["We could not find a user with that email"],
                    "email": args["email"],
                    "password": args["password"],
                },
            )

        if pbkdf2_sha512.verify(args["password"], row["password"]) is True:
            return await login_user(request, row["id"], args["email"], row["session_duration"])

        # email is right password is wrong
        return await render_template(
            "onboarding",
            request,
            {"password_error": ["Invalid password"], "email": args["email"]},
            status=401,
        )

    return await render_template("onboarding", request, {"type": "login", "email": request.cookies.get("email")})


@bp.get("/logout", name="logout")
@requires_auth(redirect=True)
async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get("_session")
    res = web.HTTPFound("/")
    res.del_cookie("_session")
    await delete_session(get_db(request), token=UUID(token))
    return res
