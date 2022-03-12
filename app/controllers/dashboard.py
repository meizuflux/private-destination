import aiohttp_jinja2
from app.routing import Controller, view
from aiohttp import web

from app.utils.auth import requires_auth, AuthenticationScheme

class Dashboard(Controller):
    @view()
    class Index(web.View):
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        @aiohttp_jinja2.template("dashboard.html")
        async def get(self):
            return {}

    @view("shortner")
    class Shortner(web.View):
        async def get(self):
            return web.json_response({"message": "unfinished"})

    @view("settings")
    class Settings(web.View):
        @aiohttp_jinja2.template("settings.html")
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        async def get(self):
            return {}