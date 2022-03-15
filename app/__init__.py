from uuid import UUID
from aiohttp import web, ClientSession
from app import controllers
import asyncio
import aiohttp_jinja2
from jinja2 import FileSystemLoader

from aiohttp_apispec import (
    setup_aiohttp_apispec,
    validation_middleware,
    match_info_schema
)
from sys import argv
from yaml import safe_load
from app.utils.auth import AuthenticationScheme, Credentials, requires_auth
from app.utils.auth.providers import providers
from app.utils.db import create_pool
from marshmallow import Schema, fields

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

sentry_sdk.init(
      dsn="https://c51ee48c5ae341ba9a16d57657fc89b0@o1007379.ingest.sentry.io/6237979",
      integrations=[AioHttpIntegration()],
      send_default_pii=True
)

class ShortnerMatchInfo(Schema):
    key = fields.Str(required=True)

async def verify_user(
    request,
    scheme: AuthenticationScheme,
    admin: bool,
    redirect: bool,
    wants_user_info: bool
):
    session = request.cookies.get("_session")
    if session is None:
        if redirect is True:
            return web.HTTPTemporaryRedirect("/login")
        return web.HTTPUnauthorized()

    if wants_user_info is True or admin is True:
        user = await request.app["db"].fetch_user_by_session(UUID(session))
        if user is None:
            if redirect is True:
                return web.HTTPTemporaryRedirect("/login")
            return web.HTTPUnauthorized()
        if admin is True and user["admin"] is False:
            return web.HTTPUnauthorized()
        request["user"] = user
    else:
        valid = await request.app["db"].validate_session(UUID(session))
        if valid is not True:
            if redirect is True:
                return web.HTTPTemporaryRedirect("/login")
            return web.HTTPUnauthorized()


@web.middleware
async def authentication_middleware(request, handler):
    fn = handler
    if hasattr(handler, request.method.lower()):
        fn = getattr(handler, request.method.lower())

    if hasattr(fn, "requires_auth"):
        verify = await verify_user(request, fn.auth["scheme"], fn.auth["admin"], fn.auth["redirect"], fn.auth["wants_user_info"])
        if verify is not None:
            return verify

    return await handler(request)

async def index(_):
    return web.HTTPTemporaryRedirect("/dashboard")

@aiohttp_jinja2.template("login.html")
async def login(request):
    providers = []
    for key, provider in request.app["oauth_providers"].items():
        providers.append({"key": key, "name": provider.name})
    return {"providers": providers}

@match_info_schema(ShortnerMatchInfo)
async def shortner(request):
    key = request["match_info"]["key"]
    destination = await request.app["db"].fetchval("SELECT destination FROM urls WHERE key = $1", key)
    if destination is None:
        return web.Response(body="No shortened URL with that key was found.")

    asyncio.get_event_loop().create_task(request.app["db"].execute("UPDATE urls SET clicks = clicks + 1 WHERE key = $1", key))

    return web.HTTPTemporaryRedirect(destination)

async def app_factory():
    app = web.Application(middlewares=[authentication_middleware, validation_middleware])

    app.router.add_get("/", index)
    app.router.add_get("/login", login)

    for controller in controllers.all():
        controller.add_routes(app)

    app.router.add_get("/{key}", shortner)

    setup_aiohttp_apispec(
        app=app, 
        title="Documentation",
        version="v1",
        url="/api/docs/swagger.json",
        swagger_path="/api/docs",
        in_place=True
    )

    aiohttp_jinja2.setup(
        app,
        enable_async=True,
        loader=FileSystemLoader("./templates"),
        context_processors=[aiohttp_jinja2.request_processor]
    )
    env = aiohttp_jinja2.get_env(app)
    env.globals.update(enumerate=enumerate, len=len)

    app["dev"] = "adev" in argv[0]
    with open("config.yml") as f:
        loaded = safe_load(f)

        if app["dev"] is True:
            config = loaded["dev"]
        else:
            config = loaded["prod"]

    if app["dev"] is True:
        app.router.add_static("/static", "dist")

    for resource in app.router.resources():
        print(resource.canonical)

    app["config"] = config
    app["oauth_providers"] = {}

    for name, cls in providers.items():
        app["oauth_providers"][name] = cls(credentials=Credentials(app["config"][name]["client_id"], app["config"][name]["client_secret"]))

    app["db"] = await create_pool(app, dsn=app["config"]["postgres_dsn"])
    app["session"] = ClientSession()
    with open("schema.sql") as f:
        await app["db"].execute(f.read())

    async def close(a):
        await a["session"].close()
        await a["db"].close()
        
    app.on_cleanup.append(close)

    return app

if __name__ == "__main__":
    web.run_app(app_factory(), host="localhost", port=8000)

def main():
    web.run_app(app_factory(), host="localhost", port=8000)
