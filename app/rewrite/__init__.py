from aiohttp import web, ClientSession
from app.rewrite import controllers

from aiohttp_apispec import (
    setup_aiohttp_apispec,
    validation_middleware,
)
from sys import argv
from yaml import safe_load
from app.utils.auth import Credentials
from app.utils.auth.providers import providers
from app.utils.db import create_pool

async def app_factory():
    app = web.Application()
    app.middlewares.append(validation_middleware)

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

    app["config"] = config
    app["oauth_providers"] = { }

    for name, cls in providers.items():
        app["oauth_providers"][name] = cls(credentials=Credentials(app["config"][name]["client_id"], app["config"][name]["client_secret"]))

    app["db"] = await create_pool(app, dsn=app["config"]["postgres_dsn"])
    app["session"] = ClientSession()
    with open("schema.sql") as f:
        await app["db"].execute(f.read())

    return app

if __name__ == "__main__":
    web.run_app(app_factory(), host="localhost", port=8000)
