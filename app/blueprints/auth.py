from uuid import UUID

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from aiohttp_jinja2 import render_template_async
from marshmallow import Schema, ValidationError, fields
from passlib.hash import pbkdf2_sha512
from ua_parser import user_agent_parser

from app.models.auth import LoginSchema
from app.routing import Blueprint
from app.utils import Status
from app.utils.auth import create_user, requires_auth, verify_user
from app.utils.db import delete_session, get_hash_and_id_by_email, insert_session
from app.utils.forms import parser


class InviteCodeSchema(Schema):
    code = fields.UUID()


async def login_user(request: web.Request, user_id: int) -> web.Response:
    metadata = user_agent_parser.Parse(request.headers.getone("User-Agent"))
    browser = metadata["user_agent"]["family"]
    operating_system = metadata["os"]["family"]

    # get ip from forwarded for header or remote address
    ip_address = request.headers.getone("X-Forwarded-For", None)
    if ip_address is None:
        transport = request.transport
        if transport is not None:
            peername = transport.get_extra_info("peername")
            if peername is not None:
                ip_address, _ = peername

    if ip_address is not None:
        split = ip_address.split(",")  # for some reason the ip might have a comma
        if len(split) > 0:
            ip_address = split[0]  # no idea why this happens but it does

    uuid = await insert_session(request.app["db"], user_id=user_id, browser=browser, os=operating_system, ip=ip_address)

    res = web.HTTPFound("/dashboard")
    res.set_cookie(
        name="_session",
        value=str(uuid),
        max_age=60 * 60 * 24,  # one day
        httponly=True,
        secure=not request.app["dev"],
        samesite="strict",  # using this lets me not need to setup csrf and whatnot
    )

    return res


bp = Blueprint("/auth")


@bp.get("/invite/{code}")
@match_info_schema(InviteCodeSchema())
async def invite(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None):
        return web.HTTPFound("/dashboard")
    return web.HTTPFound(f"/auth/login?code={request['match_info']['code']}")


@bp.route("/signup", methods=["GET", "POST"])
@querystring_schema(InviteCodeSchema())
async def signup(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    invite_code = request["querystring"].get("code", "")

    if request.method == "POST":
        ret = await create_user(
            request, template="onboarding.html.jinja", extra_ctx={"type": "signup", "invite_code": invite_code}
        )
        if ret[0] is Status.ERROR:
            return ret[1]

        return await login_user(request, ret[1])

    return await render_template_async("onboarding.html.jinja", request, {"type": "signup", "invite_code": invite_code})


@bp.route("/login", methods=["GET", "POST"])
async def login(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    if request.method == "POST":
        try:
            args = await parser.parse(LoginSchema(), request, locations=["form"])
        except ValidationError as error:
            return await render_template_async(
                "onboarding.html.jinja",
                request,
                {
                    "email_error": error.messages.get("email"),
                    "password_error": error.messages.get("password"),
                    "type": "login",
                    "email": error.data.get("email"),
                    "password": error.data.get("password"),
                },
                status=400,
            )

        row = await get_hash_and_id_by_email(request.app["db"], email=args["email"])
        if row is None:
            return await render_template_async(
                "onboarding.html.jinja",
                request,
                {
                    "email_error": ["We could not find a user with that email"],
                    "email": args["email"],
                    "password": args["password"],
                },
            )

        if pbkdf2_sha512.verify(args["password"], row["password"]) is True:
            return await login_user(request, row["id"])

        # email is right password is wrong
        return await render_template_async(
            "onboarding.html.jinja",
            request,
            {"password_error": ["Invalid password"], "email": args["email"]},
            status=401,
        )

    return await render_template_async("onboarding.html.jinja", request, {"type": "login"})


@bp.get("/logout")
@requires_auth(redirect=True)
async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get("_session")
    res = web.HTTPFound("/")
    res.del_cookie("_session")
    await delete_session(request.app["db"], token=UUID(token))
    return res
