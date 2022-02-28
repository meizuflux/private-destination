from enum import Enum
from uuid import UUID
from aiohttp import web, ClientSession
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_urldispatcher import AbstractRoute, MatchInfoError, PlainResource, ResourceRoute, UrlMappingMatchInfo
from app import controllers

from aiohttp_apispec import (
    setup_aiohttp_apispec,
    validation_middleware,
)
from sys import argv
from yaml import safe_load
from app.utils.auth import Credentials, User
from app.utils.auth.providers import providers
from app.utils.db import create_pool

class AuthenticationScheme(Enum):
    SESSION = 1
    API_KEY = 2
    BOTH = 3

@web.middleware
async def authentication_middleware(request, handler):
    fn = handler
    if hasattr(handler, request.method.lower()):
        fn = getattr(handler, request.method.lower())

    if hasattr(fn, "requires_auth"):
        print(fn.requires_auth, fn.admin)
        session = request.cookies.get("_session")
        if session is None:
            return web.HTTPTemporaryRedirect("/login")
        user = await request.app["db"].fetch_user(UUID(session))
        if user is None:
            return web.HTTPTemporaryRedirect("/login")
        request["user"] = user


    return await handler(request)

def requires_auth(*, admin: bool = False, scheme: AuthenticationScheme = AuthenticationScheme.BOTH):
    def deco(fn):
        setattr(fn, "requires_auth", True)
        setattr(fn, "admin", admin)
        setattr(fn, "auth_scheme", scheme)
        return fn
    return deco

@requires_auth()
async def index(request) -> web.Response:
    return web.json_response({"message": "hello"})

class Tset(web.View):
    @requires_auth()
    async def get(self):
        return web.json_response({})

async def all(request):
    return web.json_response({})

with open("frontend/dist/index.html", encoding="utf8") as indexs:
    html = indexs.read()

async def catch_all(request):
    if str(request.rel_url).startswith("/api/") or str(request.rel_url) == "/api":
        return web.HTTPNotFound()
    return web.Response(text=html, content_type='text/html')

async def app_factory():
    app = web.Application(middlewares=[authentication_middleware, validation_middleware])

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


    for resource in app.router.resources():
        print(resource.canonical)

    app["dev"] = "adev" in argv[0]
    with open("config.yml") as f:
        loaded = safe_load(f)

        if app["dev"] is True:
            config = loaded["dev"]
        else:
            config = loaded["prod"]

    if app["dev"] is True:
        app.router.add_static("/assets", "frontend/dist/assets")

    app.router.add_get("/{tail:.*}", catch_all)

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
