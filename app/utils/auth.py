from uuid import UUID

from aiohttp import web

from app.utils import Scopes
from app.utils.db import (
    select_api_key_exists,
    select_session_exists,
    select_user_by_api_key,
    select_user_by_session,
)


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
            if scopes is None:
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
                return HTTPPendingAuthorization()

        if admin is True and user["admin"] is False:
            return web.HTTPForbidden()

    request["user"] = user
    return user
