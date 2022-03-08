import aiohttp_jinja2
from app.routing import Controller, view
from aiohttp import web

class Dashboard(Controller):
    @view()
    class Index(web.View):
        @aiohttp_jinja2.template("dashboard.html")
        async def get(self):
            return {}

    @view("shortner")
    class Shortner(web.View):
        async def get(self):
            return web.json_response({"message": "unfinished"})