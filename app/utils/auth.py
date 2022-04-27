from secrets import choice
from string import ascii_letters, digits
from typing import Literal, Tuple
from uuid import UUID

from aiohttp import web
from aiohttp_jinja2 import render_template_async
from asyncpg import Record, UniqueViolationError
from marshmallow import ValidationError
from passlib.hash import pbkdf2_sha512

from app.models.auth import SignUpSchema, UsersEditSchema
from app.utils import Scopes, Status
from app.utils.db import (
    ConnOrPool,
    insert_user,
    select_api_key_exists,
    select_session_exists,
    select_user_by_api_key,
    select_user_by_session,
    update_user,
)
from app.utils.forms import parser

API_KEY_VALID_CHARS = ascii_letters + digits + "!@%^&?<>:;+=-_~"


async def generate_api_key(database: ConnOrPool) -> str:
    while True:
        api_key = "".join(choice(API_KEY_VALID_CHARS) for _ in range(256))
        if await select_api_key_exists(database, api_key=api_key) is False:
            break
    return api_key


def requires_auth(
    *,
    admin: bool = False,
    redirect: bool = False,
    scopes: Scopes = None,
):
    if scopes is not None:
        if isinstance(scopes, str):
            scopes = [scopes]

    if admin is True:
        if admin is True:
            if scopes is None:
                scopes = ["admin"]
            elif scopes[0] != "*":
                scopes.append("admin")

    def deco(function):
        setattr(function, "requires_auth", True)
        setattr(
            function,
            "auth",
            {"admin": admin, "redirect": redirect, "scopes": scopes},
        )
        return function

    return deco


async def verify_user(request: web.Request, *, admin: bool, redirect: bool, scopes: Scopes):
    async def by_session():
        session = request.cookies.get("_session")
        if session is not None:
            if scopes is None and admin is not True:
                return await select_session_exists(request.app["db"], token=UUID(session))
            user = await select_user_by_session(request.app["db"], token=UUID(session), scopes=scopes)
            return user

    async def by_api_key():
        api_key = request.headers.get("x-api-key")
        if api_key is not None:
            if scopes is None and admin is not True:
                return await select_api_key_exists(request.app["db"], api_key=api_key)
            user = await select_user_by_api_key(request.app["db"], api_key=api_key, scopes=scopes)
            return user

    user = await by_session() or await by_api_key()

    if not user:
        if redirect is True:
            return web.HTTPFound("/")
        return web.HTTPUnauthorized()
    if scopes is not None:
        if admin is True and user["admin"] is False:
            return web.HTTPForbidden()

    request["user"] = user
    return user


async def create_user(
    request: web.Request,
    *,
    template: str,
    extra_ctx: dict,
) -> Tuple[Literal[Status.OK], int, str] | Tuple[Literal[Status.ERROR], web.Response]:
    try:
        args = await parser.parse(SignUpSchema(), request, locations=["form"])
    except ValidationError as error:
        ctx = {
            "email_error": error.messages.get("email"),
            "invite_code_error": error.messages.get("invite_code"),
            "email": error.data.get("email"),
            "invite_code": error.data.get("invite_code"),
            "password": error.data.get("password"),
        }
        ctx.update(extra_ctx)

        return Status.ERROR, await render_template_async(template, request, ctx, status=400)

    try:
        async with request.app["db"].acquire() as conn:
            invite = await conn.fetchrow(
                "SELECT used_by, required_email FROM invites WHERE code = $1", args["invite_code"]
            )
            if invite["used_by"] is not None:
                ctx = {"invite_code_error": ["This invite code has already been used"]}
                ctx.update(extra_ctx)
                return Status.ERROR, await render_template_async(template, request, ctx, status=409)

            if invite["required_email"] is not None and invite["required_email"] != args["email"]:
                ctx = {
                    "invite_code_error": [
                        "Your email does not match the email specified by the owner of the invite code"
                    ]
                }
                ctx.update(extra_ctx)
                return Status.ERROR, await render_template_async(template, request, ctx, status=409)

            user_id = await insert_user(
                conn,
                email=args["email"],
                api_key=await generate_api_key(conn),
                hashed_password=pbkdf2_sha512.hash(args["password"]),
            )

            await conn.execute("UPDATE invites SET used_by = $1 WHERE code = $2", user_id, args["invite_code"])
    except UniqueViolationError:
        ctx = {
            "email_error": ["A user with this email already exists"],
            "email": args["email"],
            "password": args["password"],
        }
        ctx.update(extra_ctx)
        return Status.ERROR, await render_template_async(template, request, ctx, status=409)

    return Status.OK, user_id, args["admin"]


async def edit_user(
    request: web.Request,
    *,
    old_user: Record,
    template: str,
    extra_ctx: dict = {},
) -> Tuple[Literal[Status.OK], None] | Tuple[Literal[Status.ERROR], web.Response]:
    try:
        args = await parser.parse(UsersEditSchema(), request, locations=["form"])
    except ValidationError as error:
        ctx = {
            "email_error": error.messages.get("email"),
            "id": old_user["id"],
            "email": error.data.get("email"),
            "admin": old_user["admin"],
            "joined": old_user["joined"],
        }
        ctx.update(extra_ctx)

        return Status.ERROR, await render_template_async(
            template,
            request,
            ctx,
            status=400,
        )

    try:
        await update_user(
            request.app["db"],
            user_id=old_user["id"],
            email=args["email"],
        )
    except UniqueViolationError:
        ctx = {
            "email_error": ["A user with this email already exists"],
            "id": old_user["id"],
            "email": args["email"],
            "admin": old_user["admin"],
            "joined": old_user["joined"],
        }
        ctx.update(extra_ctx)
        return Status.ERROR, await render_template_async(
            template,
            request,
            ctx,
            status=400,
        )

    return Status.OK, None
