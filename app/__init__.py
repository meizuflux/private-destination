from sys import argv

import aiohttp_jinja2
import sentry_sdk
from aiohttp import ClientSession, web
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware
from asyncpg import create_pool
from jinja2 import FileSystemLoader
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from yaml import safe_load

from app.utils.auth import verify_user

sentry_sdk.init(
    dsn="https://c51ee48c5ae341ba9a16d57657fc89b0@o1007379.ingest.sentry.io/6237979",
    integrations=[AioHttpIntegration()],
    send_default_pii=True,
)

from app import blueprints


def truncate(text: str, limit: int):
    return text[:limit - 3] + "..." if len(text) > limit else text


@web.middleware
async def authentication_middleware(request, handler):
    fn = handler
    if hasattr(handler, request.method.lower()):
        fn = getattr(handler, request.method.lower())

    if hasattr(fn, "requires_auth"):
        error = await verify_user(
            request,
            admin=fn.auth["admin"],
            redirect=fn.auth["redirect"],
            scopes=fn.auth["scopes"],
            needs_authorization=fn.auth["needs_authorization"],
        )
        if isinstance(error, web.HTTPException):
            return await handle_errors(request, error)

    return await handler(request)


async def handle_errors(request: web.Request, error: web.HTTPException):
    if not str(request.rel_url).startswith("/api") and error.status in {
        403,
        404,
        499,
        500,
    }:
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
    app.router.add_routes(blueprints.auth.bp)
    app.router.add_routes(blueprints.dashboard.bp)
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

    app["db"] = await create_pool(dsn=app["config"]["postgres_dsn"])
    app["session"] = ClientSession()
    with open("schema.sql") as f:
        await app["db"].execute(f.read())

    async def close(a):
        await a["session"].close()
        await a["db"].close()

    app.on_cleanup.append(close)

    return app
