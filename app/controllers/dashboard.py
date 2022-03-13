from aiohttp_apispec import querystring_schema
import aiohttp_jinja2
from app.routing import Controller, view
from aiohttp import web

from app.utils.auth import requires_auth, AuthenticationScheme
from marshmallow import Schema, fields, validate

class ShortnerQuerystring(Schema):
    page = fields.Integer(required=False)
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sort = fields.String(validate=validate.OneOf({"key", "destination", "views", "creation_date"}))

class Dashboard(Controller):
    @view()
    class Index(web.View):
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        @aiohttp_jinja2.template("dashboard.html")
        async def get(self):
            return {}

    @view("shortner")
    class Shortner(web.View):
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        @querystring_schema(ShortnerQuerystring)
        @aiohttp_jinja2.template("shortner.html")
        async def get(self):
            current_page = self.request["querystring"].get("page", 1)
            direction = self.request["querystring"].get("direction", "desc")
            sort = self.request["querystring"].get("sort", "creation_date")

            values = [
                {
                    "key": "dasfajsdbhb341",
                    "destination": "https://google.com",
                    "views": 1000,
                    "creation_date": "14 July 2007"
                },
                {
                    "key": "a21b341",
                    "destination": "https://meizuflux",
                    "views": 2000,
                    "creation_date": "14 July 2008"
                },
                {
                    "key": "412fgsa",
                    "destination": "https://discord.com",
                    "views": 3000,
                    "creation_date": "14 July 2009"
                }
            ]

            return {"current_page": current_page, "max_pages": 10, "values": values, "direction": "asc" if direction == "desc" else "desc", "last_sort": sort}

    @view("settings")
    class Settings(web.View):
        @aiohttp_jinja2.template("settings.html")
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        async def get(self):
            return {}