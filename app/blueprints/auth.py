from asyncpg import Pool
import string
from secrets import choice
from uuid import UUID

from aiohttp import web
from aiohttp_jinja2 import render_template_async
from asyncpg import UniqueViolationError
from marshmallow import Schema, ValidationError, fields, validate
from passlib.hash import pbkdf2_sha512
from ua_parser import user_agent_parser

from app.routing import Blueprint
from app.utils.auth import requires_auth, verify_user
from app.utils.db import delete_session, get_hash_and_id_by_email, insert_session, insert_user, select_api_key_exists
from app.utils.forms import parser


all_chars = string.ascii_letters + string.digits + "!@%^&?<>:;+=-_~"


async def generate_api_key(db: Pool) -> str:
    while True:
        api_key = "".join(choice(all_chars) for _ in range(128))
        if await select_api_key_exists(db, api_key=api_key) is False:
            break
    return api_key


async def login_user(request: web.Request, user_id: int) -> web.Response:
    metadata = user_agent_parser.Parse(request.headers.getone("User-Agent"))
    browser = metadata["user_agent"]["family"]
    os = metadata["os"]["family"]

    uuid = await insert_session(
        request.app["db"],
        browser=browser,
        os=os
    )

    res = web.HTTPFound("/dashboard")
    res.set_cookie(
        name="_session",
        value=str(uuid),
        max_age=60 * 60 * 24,  # one day
        httponly=True,
        secure=not request.app["dev"],
        samesite="strict",
    )

    return res

class LoginForm(Schema):
    email = fields.Email(required=True)
    password = fields.Field(require=True)

class SignUpForm(LoginForm):
    username = fields.String(validate=validate.Length(3, 32), required=True)


bp = Blueprint("/auth")


@bp.get("/signup")
@bp.post("/signup")
async def signup(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    if request.method == "POST":
        try:
            args = await parser.parse(SignUpForm(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "onboarding.html",
                request,
                {
                    "username_error": e.messages.get("username"),
                    "email_error": e.messages.get("email"),
                    "password_error": e.messages.get("password"),
                    "type": "signup",
                },
            )

        try:
            user_id = await insert_user(
                request.app["db"],
                user={
                    "username": args["username"],
                    "email": args["email"],
                    "api_key": await generate_api_key(request.app["db"]),
                },
                hashed_password=pbkdf2_sha512.hash(args["password"]),
            )
        except UniqueViolationError:
            return await render_template_async(
                "onboarding.html", request, {"type": "signup", "email_error": ["A user with this email already exists"]}
            )

        return await login_user(request, user_id)

    return await render_template_async("onboarding.html", request, {"type": "signup"})


@bp.get("/login")
@bp.post("/login")
async def login(request: web.Request) -> web.Response:
    if await verify_user(request, admin=False, redirect=False, scopes=None) is True:
        return web.HTTPFound("/dashboard")

    if request.method == "POST":
        try:
            args = await parser.parse(LoginForm(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "onboarding.html",
                request,
                {"email_error": e.messages.get("email"), "password_error": e.messages.get("password"), "type": "login"},
            )

        row = await get_hash_and_id_by_email(
            request.app["db"],
            email=args["email"]
        )
        if row is not None:
            if pbkdf2_sha512.verify(args["password"], row["password"]) is True:
                return await login_user(request, row["id"])

            return await render_template_async("onboarding.html", request, {"password_error": ["Invalid password"]})

        return await render_template_async(
            "onboarding.html", request, {"email_error": ["We could not find a user with that email"]}
        )

    return await render_template_async("onboarding.html", request, {"type": "login"})


@bp.get("/logout")
@requires_auth(redirect=True)
async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get("_session")
    res = web.HTTPFound("/")
    res.del_cookie("_session")
    await delete_session(
        request.app["db"],
        token=UUID(token)
    )
    return res
