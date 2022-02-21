from aiohttp import ClientSession
from blacksheep import Application


async def before_start(application: Application) -> None:
    print("Before start")

    application.state["session"] = ClientSession()


async def after_start(application: Application) -> None:
    print("After start")
    print(application.router.routes)


async def on_stop(application: Application) -> None:
    print("On stop")

