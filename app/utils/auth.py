from secrets import choice
from string import ascii_letters, digits
from typing import Any, Callable, Literal, Tuple
from uuid import UUID

from aiohttp import web
from asyncpg import Record, UniqueViolationError
from marshmallow import ValidationError
from passlib.hash import pbkdf2_sha512

from app.models.auth import SignUpSchema, UsersEditSchema
from app.templating import render_template
from app.utils import Scopes, Status
from app.utils.db import (
    ConnOrPool,
    get_db,
    insert_user,
    select_api_key_exists,
    select_session_exists,
    select_user_by_api_key,
    select_user_by_session,
    update_user,
)
from app.utils.forms import parser
from app.utils.time import get_seconds

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
) -> Callable[[Any], Any]:  # TODO: type hint this and deco
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


async def verify_user(
    request: web.Request, *, admin: bool, redirect: bool, scopes: Scopes
) -> dict[str, str | int | bool] | bool | web.Response:
    async def by_session():
        session = request.cookies.get("_session")
        if session is not None:
            if scopes is None and admin is not True:
                return await select_session_exists(get_db(request), token=UUID(session))
            user = await select_user_by_session(get_db(request), token=UUID(session), scopes=scopes)
            return user

    async def by_api_key():
        api_key = request.headers.get("x-api-key")
        if api_key is not None:
            if scopes is None and admin is not True:
                return await select_api_key_exists(get_db(request), api_key=api_key)
            user = await select_user_by_api_key(get_db(request), api_key=api_key, scopes=scopes)
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
        messages = error.normalized_messages()
        ctx = {
            "email_error": messages.get("email"),
            "invite_code_error": messages.get("invite_code"),
            "email": error.data.get("email"),
            "invite_code": error.data.get("invite_code"),
            "password": error.data.get("password"),
        }
        ctx.update(extra_ctx)

        return Status.ERROR, await render_template(template, request, ctx, status=400)

    try:
        async with get_db(request).acquire() as conn:
            invite = await conn.fetchrow(
                "SELECT used_by, required_email FROM invites WHERE code = $1", args["invite_code"]
            )
            if invite["used_by"] is not None:
                ctx = {"invite_code_error": ["This invite code has already been used"]}
                ctx.update(extra_ctx)
                return Status.ERROR, await render_template(template, request, ctx, status=409)

            if invite["required_email"] is not None and invite["required_email"] != args["email"]:
                ctx = {
                    "invite_code_error": [
                        "Your email does not match the email specified by the owner of the invite code"
                    ]
                }
                ctx.update(extra_ctx)
                return Status.ERROR, await render_template(template, request, ctx, status=409)

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
        return Status.ERROR, await render_template(template, request, ctx, status=409)

    return Status.OK, user_id, args["admin"]


async def edit_user(
    request: web.Request,
    *,
    old_user: Record,
    session_duration: tuple[int, str],
    template: str,
    extra_ctx: dict = {},
) -> Tuple[Literal[Status.OK], None] | Tuple[Literal[Status.ERROR], web.Response]:
    try:
        args = await parser.parse(UsersEditSchema(), request, locations=["form"])
    except ValidationError as error:
        messages = error.normalized_messages()
        ctx = {
            "email_error": messages.get("email"),
            "session_duration_amount_error": messages.get("session_duration_amount"),
            "session_duration_unit_error": messages.get("session_duration_unit"),
            "id": old_user["id"],
            "email": error.data.get("email"),
            "admin": old_user["admin"],
            "joined": old_user["joined"],
            "session_duration": {"amount": session_duration[0], "unit": session_duration[1]},
        }

        ctx.update(extra_ctx)

        return Status.ERROR, await render_template(
            template,
            request,
            ctx,
            status=400,
        )

    try:
        await update_user(
            get_db(request),
            user_id=old_user["id"],
            session_duration=get_seconds(args["session_duration_amount"], args["session_duration_unit"]),
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
        return Status.ERROR, await render_template(
            template,
            request,
            ctx,
            status=400,
        )

    return Status.OK, None
