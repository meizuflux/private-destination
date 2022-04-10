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
    return f'{text[:limit - 3]}...' if len(text) > limit else text

async def handle_errors(request: web.Request, error: web.HTTPException):
    if not str(request.rel_url).startswith("/api") and error.status in {403, 404, 499, 500}:
        return await aiohttp_jinja2.render_template_async(
            f"errors/{error.status}.html", request, {}, status=error.status
        )

    raise error


@web.middleware
async def authentication_middleware(request: web.Request, handler):
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
    app.router.add_routes(blueprints.dashboard.settings.bp)
    app.router.add_routes(blueprints.dashboard.shortener.bp)
    app.router.add_routes(blueprints.admin.users.bp)

    # has to go last since it has a catch-all
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
        loader=FileSystemLoader("./views"),
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

    async def security_signal(request: web.Request, response: web.Response):
        response.headers["Permissions-Policy"] = "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), camera=(), cross-origin-isolated=(self), display-capture=(), document-domain=(), encrypted-media=(self), execution-while-not-rendered=(), execution-while-out-of-viewport=(), fullscreen=(self), geolocation=(), gyroscope=(), keyboard-map=*, magnetometer=(), microphone=(), midi=(), navigation-override=(), payment=(), picture-in-picture=(self), publickey-credentials-get=(self), screen-wake-lock=(self), sync-xhr=*, usb=(), web-share=(), xr-spatial-tracking=(), clipboard-read=(), clipboard-write=(self), gamepad=(), speaker-selection=(self)"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src cdnjs.cloudflare.com" # TODO: add report-uri
        if app["dev"] is False:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

    app.on_response_prepare.append(security_signal)

    async def close(a):
        await a["session"].close()
        await a["db"].close()

    app.on_cleanup.append(close)

    return app
