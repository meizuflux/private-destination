from datetime import datetime
from typing import List, TypedDict, Union
from uuid import UUID

from aiohttp import web

Scopes = Union[List[str], None, str]


class User(TypedDict):
    id: str
    username: str
    email: str
    api_key: str
    joined: datetime
    authorized: bool
    admin: bool


def requires_auth(
    *,
    admin: bool = False,
    redirect: bool = False,
    scopes: Scopes = None,  # a tuple represents the columns, a false means don't fetch the user, and true means to get all columns (*)
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
        setattr(fn, "auth", {"admin": admin, "redirect": redirect, "scopes": scopes})
        return fn

    return deco


class HTTPPendingAuthorization(web.HTTPClientError):
    status_code = 499
    reason = "Pending Authorization"


async def verify_user(request: web.Request, *, admin: bool, redirect: bool, scopes: Scopes):
    async def by_session():
        session = request.cookies.get("_session")
        if session is not None:
            if scopes is not None or admin is True:
                user = await request.app["db"].fetch_user_by_session(UUID(session), scopes)
                return user
            else:
                print("here")
                return await request.app["db"].validate_session(UUID(session))

    async def by_api_key():
        api_key = request.headers.get("x-api-key")
        if api_key is not None:
            if scopes is not None or admin is True:
                user = await request.app["db"].fetch_user_by_api_key(api_key, scopes)
                return user
            else:
                return await request.app["db"].validate_api_key(api_key)

    user = await by_session() or await by_api_key()

    if not user:
        if redirect is True:
            return web.HTTPFound("/auth/login")
        return web.HTTPUnauthorized()
    if scopes is not None:
        if user["authorized"] is False:
            return HTTPPendingAuthorization()

        if admin is True and user["admin"] is False:
            return web.HTTPForbidden()

    request["user"] = user
    return user
