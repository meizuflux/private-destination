from aiohttp import ClientSession
from blacksheep import Application
from pprint import pprint

from yaml import dump


async def before_start(application: Application) -> None:
    print("Before start")

    application.state["session"] = ClientSession()


async def after_start(application: Application) -> None:
    final = {k.decode('utf8'): [r.pattern.decode('utf8') for r in v] for (k, v) in dict(application.router.routes).items()}

    print(dump(final))


async def on_stop(application: Application) -> None:
    print("On stop")

