from uuid import UUID
from aiohttp import web, ClientSession
from app import controllers
import aiohttp_jinja2
from jinja2 import FileSystemLoader

from aiohttp_apispec import (
    setup_aiohttp_apispec,
    validation_middleware,
)
from sys import argv
from yaml import safe_load
from app.utils.auth import AuthenticationScheme, Credentials, requires_auth
from app.utils.auth.providers import providers
from app.utils.db import create_pool

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

sentry_sdk.init(
      dsn="https://c51ee48c5ae341ba9a16d57657fc89b0@o1007379.ingest.sentry.io/6237979",
      integrations=[AioHttpIntegration()],
      send_default_pii=True
)

async def verify_user(request, scheme: AuthenticationScheme, admin: bool):
    session = request.cookies.get("_session")
    if session is None:
        return web.HTTPTemporaryRedirect("/login")
    user = await request.app["db"].fetch_user(UUID(session))
    if user is None:
        return web.HTTPTemporaryRedirect("/login")
    if admin is True and user["admin"] is False:
        return web.HTTPUnauthorized()
    request["user"] = user
    sentry_sdk.set_user({
        "id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
    })


@web.middleware
async def authentication_middleware(request, handler):
    fn = handler
    if hasattr(handler, request.method.lower()):
        fn = getattr(handler, request.method.lower())

    if hasattr(fn, "requires_auth"):
        verify = await verify_user(request, fn.auth_scheme, fn.admin)
        if verify is not None:
            return verify

    return await handler(request)

with open("frontend/dist/index.html", encoding="utf8") as indexs:
    html = indexs.read()

async def catch_all(request):
    raw_url = str(request.rel_url)
    if raw_url.startswith("/api/") or raw_url == "/api":
        return web.HTTPNotFound()
    if raw_url.startswith("/dashboard"):
        verify = await verify_user(request, AuthenticationScheme.SESSION, False)
        if verify is not None:
            return verify
    if raw_url.startswith("/admin"):
        verify = await verify_user(request, AuthenticationScheme.SESSION, True)
        if verify is not None:
            return verify
    return web.Response(text=html, content_type='text/html')

@aiohttp_jinja2.template("index.html")
async def index(request):
    return {"name": "world"}

async def app_factory():
    app = web.Application(middlewares=[authentication_middleware, validation_middleware])

    app.router.add_get("/", index)
    for controller in controllers.all():
        controller.add_routes(app)

    setup_aiohttp_apispec(
        app=app, 
        title="Documentation",
        version="v1",
        url="/api/docs/swagger.json",
        swagger_path="/api/docs",
        in_place=True
    )

    aiohttp_jinja2.setup(app, enable_async=True, loader=FileSystemLoader("./templates"))

    app["dev"] = "adev" in argv[0]
    with open("config.yml") as f:
        loaded = safe_load(f)

        if app["dev"] is True:
            config = loaded["dev"]
        else:
            config = loaded["prod"]

    if app["dev"] is True:
        app.router.add_static("/assets", "frontend/dist/assets")
        app.router.add_static("/static", "dist")

    app.router.add_get("/{tail:.*}", catch_all)

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

    return app

if __name__ == "__main__":
    web.run_app(app_factory(), host="localhost", port=8000)
