from sys import argv
from typing import Any

import jinja2
import sentry_sdk
from aiohttp import ClientSession, web
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware
from asyncpg import create_pool
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from yaml import safe_load

from app import blueprints, templating
from app.routing import register_blueprint, url_for
from app.utils.auth import verify_user

sentry_sdk.init(
    dsn="https://c51ee48c5ae341ba9a16d57657fc89b0@o1007379.ingest.sentry.io/6237979",
    integrations=[AioHttpIntegration()],
    send_default_pii=True,
)


def truncate(text: str, limit: int) -> str:
    return f"{text[:limit - 3]}..." if len(text) > limit else text


async def handle_errors(request: web.Request, error: web.HTTPException) -> web.Response:
    if not str(request.rel_url).startswith("/api") and error.status in {403, 404, 500}:
        return await templating.render_template(f"errors/{error.status}", request, status=error.status)

    raise error


@web.middleware
async def authentication_middleware(request: web.Request, handler):
    function = handler
    if hasattr(handler, request.method.lower()):
        function = getattr(handler, request.method.lower())

    if hasattr(function, "requires_auth"):
        error = await verify_user(
            request,
            admin=function.auth["admin"],
            redirect=function.auth["redirect"],
            scopes=function.auth["scopes"],
        )
        if isinstance(error, web.HTTPException):
            return await handle_errors(request, error)

    return await handler(request)


@web.middleware
async def exception_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException as error:  # handle exceptions here
        return await handle_errors(request, error)


@jinja2.pass_context
def __url_for(context, *args, **kwargs) -> str:
    return url_for(context["app"], *args, **kwargs)


async def custom_processor(request: web.Request) -> dict[str, Any]:
    """Inject custom variables into jinja2 environment"""
    return {
        "user": request.get("user"),
    }


async def app_factory():
    app = web.Application(middlewares=[authentication_middleware, validation_middleware, exception_middleware])

    _blueprints = (
        blueprints.auth.bp,
        blueprints.dashboard.settings.bp,
        blueprints.dashboard.shortener.bp,
        blueprints.dashboard.notes.bp,
        blueprints.admin.users.bp,
        blueprints.admin.application.bp,
        blueprints.base.bp,  # this has to go last
    )

    for _blueprint in _blueprints:
        register_blueprint(app, _blueprint)

    app.router.add_static("/static", "dist")

    setup_aiohttp_apispec(
        app=app,
        title="Documentation",
        version="v1",
        url=None,
        swagger_path=None,
        in_place=False,
    )

    templating.setup(
        app,
        global_functions={
            "len": len,
            "truncate": truncate,
            "url_for": __url_for,
        },
        context_processors=[custom_processor],
    )

    app["dev"] = "adev" in argv[0]
    with open("config.yml", encoding="utf-8") as config_file:
        loaded = safe_load(config_file)

        if app["dev"] is True:
            config = loaded["dev"]
        else:
            config = loaded["prod"]

    app["config"] = config

    app["db"] = await create_pool(dsn=app["config"]["postgres_dsn"])
    app["session"] = ClientSession()

    async def security_signal(_: web.Request, response: web.Response) -> None:
        response.headers[
            "Permissions-Policy"
        ] = "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), camera=(), cross-origin-isolated=(self), display-capture=(), document-domain=(), encrypted-media=(self), execution-while-not-rendered=(), execution-while-out-of-viewport=(), fullscreen=(self), geolocation=(), gyroscope=(), keyboard-map=*, magnetometer=(), microphone=(), midi=(), navigation-override=(), payment=(), picture-in-picture=(self), publickey-credentials-get=(self), screen-wake-lock=(self), sync-xhr=*, usb=(), web-share=(), xr-spatial-tracking=(), clipboard-read=(), clipboard-write=(self), gamepad=(), speaker-selection=(self)"  # pylint: disable=line-too-long
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers[
            "Content-Security-Policy"
        ] = "default-src 'self' meizuflux.com *.meizuflux.com; style-src 'self' cdnjs.cloudflare.com"
        if app["dev"] is False:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

    app.on_response_prepare.append(security_signal)

    async def close(_app: web.Application) -> None:
        await _app["session"].close()
        await _app["db"].close()

    app.on_cleanup.append(close)

    return app
