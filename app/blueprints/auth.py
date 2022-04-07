from uuid import UUID

from aiohttp import web
from aiohttp_jinja2 import render_template_async
from marshmallow import ValidationError
from passlib.hash import pbkdf2_sha512
from ua_parser import user_agent_parser

from app.models.auth import LoginSchema
from app.routing import Blueprint
from app.utils import Status
from app.utils.auth import create_user, requires_auth, verify_user
from app.utils.db import delete_session, get_hash_and_id_by_email, insert_session
from app.utils.forms import parser


async def login_user(request: web.Request, user_id: int) -> web.Response:
    metadata = user_agent_parser.Parse(request.headers.getone("User-Agent"))
    browser = metadata["user_agent"]["family"]
    os = metadata["os"]["family"]

    # get ip from forwarded for header or remote address
    ip = request.headers.get("X-Forwarded-For", request.remote)

    uuid = await insert_session(request.app["db"], user_id=user_id, browser=browser, os=os, ip=ip)

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


@bp.get("/signup")
@bp.post("/signup")
async def signup(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None, needs_authorization=True) is True:
        return web.HTTPFound("/dashboard")

    if request.method == "POST":
        status, ret = await create_user(request, template="onboarding.html", extra_ctx={"type": "signup"})
        if status is Status.ERROR:
            return ret

        return await login_user(request, ret)

    return await render_template_async("onboarding.html", request, {"type": "signup"})


@bp.get("/login")
@bp.post("/login")
async def login(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None, needs_authorization=True) is True:
        return web.HTTPFound("/dashboard")

    if request.method == "POST":
        try:
            args = await parser.parse(LoginSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "onboarding.html",
                request,
                {
                    "email_error": e.messages.get("email"),
                    "password_error": e.messages.get("password"),
                    "type": "login",
                    "email": e.data.get("email"),
                    "password": e.data.get("password"),
                },
                status=400,
            )

        row = await get_hash_and_id_by_email(request.app["db"], email=args["email"])
        if row is None:
            return await render_template_async(
                "onboarding.html",
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
            "onboarding.html", request, {"password_error": ["Invalid password"], "email": args["email"]}
        )

    return await render_template_async("onboarding.html", request, {"type": "login"})


@bp.get("/logout")
@requires_auth(redirect=True, needs_authorization=False)
async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get("_session")
    res = web.HTTPFound("/")
    res.del_cookie("_session")
    await delete_session(request.app["db"], token=UUID(token))
    return res
