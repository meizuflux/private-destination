from secrets import choice
from string import ascii_letters, digits
from uuid import UUID

from aiohttp import web
from aiohttp_jinja2 import render_template_async
from asyncpg import UniqueViolationError
from marshmallow import Schema, ValidationError, fields, validate
from passlib.hash import pbkdf2_sha512

from app.utils import Scopes, Status
from app.utils.db import (
    ConnOrPool,
    insert_user,
    select_api_key_exists,
    select_session_exists,
    select_user_by_api_key,
    select_user_by_session,
)
from app.utils.forms import parser


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Field(require=True)


class SignUpSchema(LoginSchema):
    username = fields.String(validate=validate.Length(3, 32), required=True)


API_KEY_VALID_CHARS = ascii_letters + digits + "!@%^&?<>:;+=-_~"


async def generate_api_key(db: ConnOrPool) -> str:
    while True:
        api_key = "".join(choice(API_KEY_VALID_CHARS) for _ in range(256))
        if await select_api_key_exists(db, api_key=api_key) is False:
            break
    return api_key


def requires_auth(
    *,
    admin: bool = False,
    redirect: bool = False,
    scopes: Scopes = None,  # a tuple represents the columns, a false means don't fetch the user, and true means to get all columns (*)
    needs_authorization: bool = True,
):
    if scopes is not None:
        if isinstance(scopes, str):
            scopes = [scopes]
    else:
        scopes = []
    if not (len(scopes) == 1 and scopes[0] == "*"):
        if admin is True:
            scopes.append("admin")
        scopes.append("authorized")

    def deco(fn):
        setattr(fn, "requires_auth", True)
        setattr(
            fn,
            "auth",
            {"admin": admin, "redirect": redirect, "scopes": scopes, "needs_authorization": needs_authorization},
        )
        return fn

    return deco


class HTTPPendingAuthorization(web.HTTPClientError):
    status_code = 499
    reason = "Pending Authorization"


async def verify_user(request: web.Request, *, admin: bool, redirect: bool, scopes: Scopes, needs_authorization: bool):
    async def by_session():
        session = request.cookies.get("_session")
        if session is not None:
            if scopes is not None:
                user = await select_user_by_session(request.app["db"], token=UUID(session), scopes=scopes)
                return user
            else:
                return await select_session_exists(request.app["db"], token=UUID(session))

    async def by_api_key():
        api_key = request.headers.get("x-api-key")
        if api_key is not None:
            if scopes is not None or admin is True:
                user = await select_user_by_api_key(request.app["db"], api_key=api_key, scopes=scopes)
                return user
            else:
                return await select_api_key_exists(request.app["db"], api_key=api_key)

    user = await by_session() or await by_api_key()

    if not user:
        if redirect is True:
            return web.HTTPFound("/auth/login")
        return web.HTTPUnauthorized()
    if scopes is not None:
        if needs_authorization is True:
            if user["authorized"] is False:
                return HTTPPendingAuthorization()

        if admin is True and user["admin"] is False:
            return web.HTTPForbidden()

    request["user"] = user
    return user


async def create_user(
    request: web.Request,
    *,
    template: str,
    extra_ctx: dict,
):
    try:
        args = await parser.parse(SignUpSchema(), request, locations=["form"])
    except ValidationError as e:
        ctx = {
            "username_error": e.messages.get("username"),
            "email_error": e.messages.get("email"),
            "password_error": e.messages.get("password"),
            "username": e.data.get("username"),
            "email": e.data.get("email"),
            "password": e.data.get("password"),
        }
        ctx.update(extra_ctx)

        return Status.ERROR, await render_template_async(
            template,
            request,
            ctx,
        )

    try:
        async with request.app["db"].acquire() as conn:
            user_id = await insert_user(
                conn,
                username=args["username"],
                email=args["email"],
                api_key=await generate_api_key(conn),
                hashed_password=pbkdf2_sha512.hash(args["password"]),
            )
    except UniqueViolationError:
        ctx = {
            "email_error": ["A user with this email already exists"],
            "email": args["email"],
            "password": args["password"],
        }
        ctx.update(extra_ctx)

        return Status.ERROR, await render_template_async(
            template,
            request,
            ctx,
        )
    return Status.OK, user_id
