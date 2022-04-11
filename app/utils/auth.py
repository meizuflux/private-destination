from ctypes import Union
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
    scopes: Scopes = None,
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


async def verify_user(request: web.Request, *, admin: bool, redirect: bool, scopes: Scopes, needs_authorization: bool):
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
            return web.HTTPFound("/auth/login")
        return web.HTTPUnauthorized()
    if scopes is not None:
        if needs_authorization is True:
            if user["authorized"] is False:
                return web.Response(status=499, reason="Pending Authorization")

        if admin is True and user["admin"] is False:
            return web.HTTPForbidden()

    request["user"] = user
    return user


async def create_user(
    request: web.Request,
    *,
    template: str,
    extra_ctx: dict,
) -> Tuple[Literal[Status.OK], None] | Tuple[Literal[Status.ERROR], web.Response]:
    try:
        args = await parser.parse(SignUpSchema(), request, locations=["form"])
    except ValidationError as e:
        ctx = {
            "email_error": e.messages.get("email"),
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


async def edit_user(
    request: web.Request,
    *,
    old_user: Record,
    template: str,
    extra_ctx: dict = {},
) -> Tuple[Literal[Status.OK], None] | Tuple[Literal[Status.ERROR], web.Response]:
    try:
        args = await parser.parse(UsersEditSchema(), request, locations=["form"])
    except ValidationError as e:
        ctx = {
            "email_error": e.messages.get("email"),
            "id": old_user["id"],
            "email": e.data.get("email"),
            "authorized": old_user["authorized"],
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
            authorized=args["authorized"],
        )
    except UniqueViolationError as e:
        ctx = {
            "email_error": ["A user with this email already exists"],
            "id": old_user["id"],
            "email": args["email"],
            "authorized": old_user["authorized"],
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
