from secrets import choice
from string import ascii_letters, digits
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping, MutableMapping, Tuple, overload
from uuid import UUID

from aiohttp import web
from asyncpg import Record, UniqueViolationError
from marshmallow import ValidationError
from passlib.hash import pbkdf2_sha512

from app.models.auth import SignUpSchema, UsersEditSchema
from app.templating import render_template
from app.utils import QueryScopes, Scopes, Status
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


async def is_authorized(request):
    try:
        await verify_user(request, redirect=False, scopes=None)
        return True
    except web.HTTPException:
        return False


def requires_auth(
    *, admin: bool = False, redirect: bool = False, scopes: Scopes = None
) -> Callable[[Callable], Callable]:
    if admin is True and scopes is None:
        scopes = ["admin"]
    if isinstance(scopes, str):
        scopes = [scopes]
    if admin is True and isinstance(scopes, list) and "admin" not in scopes:
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


@overload
async def verify_user(
    request: web.Request, *, admin: bool = False, redirect: bool = True, scopes: QueryScopes
) -> MappingProxyType[str, Any]:
    ...


@overload
async def verify_user(
    request: web.Request, *, admin: bool = False, redirect: bool = True, scopes: Literal[None]
) -> bool:
    ...


async def verify_user(request: web.Request, *, admin: bool = False, redirect: bool = True, scopes: Scopes):
    if admin is True and scopes is None:
        raise ValueError("Cannot determine if user is admin without any scopes")

    async def by_session():
        session = request.cookies.get("_session")
        if session is not None:
            if scopes is None:
                return await select_session_exists(get_db(request), token=UUID(session))
            return await select_user_by_session(get_db(request), token=UUID(session), scopes=["*"])

    async def by_api_key():
        api_key = request.headers.get("x-api-key")
        if api_key is not None:
            if scopes is None:
                return await select_api_key_exists(get_db(request), api_key=api_key)
            return await select_user_by_api_key(get_db(request), api_key=api_key, scopes=["*"])

    user = await by_session() or await by_api_key()

    if user is None:
        response = web.HTTPUnauthorized()
        if redirect is True:
            response.headers.add("Location", "/login")
        raise response

    if not isinstance(user, bool):
        if admin is True and user["admin"] is False:
            raise web.HTTPForbidden()

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
            "errors": error.normalized_messages(),
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
                    ],
                    "email": args["email"],
                    "password": args["password"],
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

    return Status.OK, user_id, args["email"]


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
        ctx = {
            "errors": error.normalized_messages(),
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
