from app.routing import Controller, view
from aiohttp import web

class Dashboard(Controller):
    @view()
    class Index(web.View):
        async def get(self):
            return web.json_response({"hi": "hi"})