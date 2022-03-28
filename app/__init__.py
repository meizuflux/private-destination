from sys import argv
from uuid import UUID

import aiohttp_jinja2
import sentry_sdk
from aiohttp import ClientSession, web
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware
from jinja2 import FileSystemLoader
from marshmallow import Schema, fields
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from yaml import safe_load

from app.utils.auth import Credentials, Scopes
from app.utils.auth.providers import providers
from app.utils.db import create_pool

sentry_sdk.init(
    dsn="https://c51ee48c5ae341ba9a16d57657fc89b0@o1007379.ingest.sentry.io/6237979",
    integrations=[AioHttpIntegration()],
    send_default_pii=True,
)

from app import blueprints


def truncate(text: str, limit: int):
    if len(text) > limit:
        return text[0 : limit - 3] + "..."
    return text


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
            return web.HTTPFound("/login")
        return web.HTTPUnauthorized()

    if user["authorized"] is False:
        return HTTPPendingAuthorization()

    if admin is True and user["admin"] is False:
        return web.HTTPForbidden()

    request["user"] = user


@web.middleware
async def authentication_middleware(request, handler):
    fn = handler
    if hasattr(handler, request.method.lower()):
        fn = getattr(handler, request.method.lower())

    if hasattr(fn, "requires_auth"):
        error = await verify_user(
            request, admin=fn.auth["admin"], redirect=fn.auth["redirect"], scopes=fn.auth["scopes"]
        )
        if error is not None:
            return await handle_errors(request, error)

    return await handler(request)


async def handle_errors(request: web.Request, error: web.HTTPException):
    if not str(request.rel_url).startswith("/api"):
        if error.status in {403, 404, 499, 500}:
            return await aiohttp_jinja2.render_template_async(
                f"errors/{error.status}.html", request, {}, status=error.status
            )

    raise error


@web.middleware
async def exception_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException as e:  # handle exceptions here
        return await handle_errors(request, e)


async def user_processor(request: web.Request):
    return {"user": request.get("user")}


async def app_factory():
    app = web.Application(middlewares=[authentication_middleware, validation_middleware, exception_middleware])

    # blueprints
    app.router.add_routes(blueprints.dashboard.bp)
    app.router.add_routes(blueprints.api.auth.bp)
    app.router.add_routes(blueprints.api.shortner.bp)
    app.router.add_routes(blueprints.api.users.bp)

    # default routes but it has to go last since it has a catch-all
    app.router.add_routes(blueprints.base.bp)

    setup_aiohttp_apispec(
        app=app,
        title="Documentation",
        version="v1",
        url="/api/docs/swagger.json",
        swagger_path="/api/docs",
        in_place=True,
    )

    aiohttp_jinja2.setup(
        app,
        enable_async=True,
        loader=FileSystemLoader("./templates"),
        context_processors=[aiohttp_jinja2.request_processor, user_processor],
    )
    env = aiohttp_jinja2.get_env(app)
    env.globals.update(enumerate=enumerate, len=len, truncate=truncate)

    app["dev"] = "adev" in argv[0]
    with open("config.yml") as f:
        loaded = safe_load(f)

        if app["dev"] is True:
            config = loaded["dev"]
        else:
            config = loaded["prod"]

    app.router.add_static("/static", "dist")

    app["config"] = config
    app["oauth_providers"] = {}

    for name, cls in providers.items():
        app["oauth_providers"][name] = cls(
            credentials=Credentials(app["config"][name]["client_id"], app["config"][name]["client_secret"])
        )

    app["db"] = await create_pool(app, dsn=app["config"]["postgres_dsn"])
    app["session"] = ClientSession()
    with open("schema.sql") as f:
        await app["db"].execute(f.read())

    async def close(a):
        await a["session"].close()
        await a["db"].close()

    app.on_cleanup.append(close)

    return app