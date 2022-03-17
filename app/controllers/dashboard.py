from aiohttp_apispec import querystring_schema
import aiohttp_jinja2
from app.routing import Controller, view
from aiohttp import web

from app.utils.auth import requires_auth, AuthenticationScheme
from marshmallow import Schema, fields, validate

class ShortnerQuerystring(Schema):
    page = fields.Integer(required=False)
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sort = fields.String(validate=validate.OneOf({"key", "destination", "clicks", "creation_date"}))

class Dashboard(Controller):
    @view()
    class Index(web.View):
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        @aiohttp_jinja2.template("dashboard.html")
        async def get(self):
            urls = await self.request.app["db"].get_short_url_count(self.request["user"]["user_id"])
            return {"url_count": urls}

    @view("shortner")
    class Shortner(web.View):
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        @querystring_schema(ShortnerQuerystring)
        @aiohttp_jinja2.template("shortner.html")
        async def get(self):
            current_page = self.request["querystring"].get("page", 1) - 1
            direction = self.request["querystring"].get("direction", "desc")
            sort = self.request["querystring"].get("sort", "creation_date")

            urls = await self.request.app["db"].get_short_urls(
                sort=sort.lower(),
                direction=direction.upper(),
                owner=self.request["user"]["user_id"],
                offset=current_page * 50
            )
            max_pages = await self.request.app["db"].get_short_url_max_pages(self.request["user"]["user_id"])

            return {
                "current_page": current_page + 1,
                "max_pages": max_pages,
                "values": urls,
                "direction": "asc" if direction == "desc" else "desc", "last_sort": sort
            }

    @view("settings")
    class Settings(web.View):
        @aiohttp_jinja2.template("settings.html")
        @requires_auth(scheme=AuthenticationScheme.SESSION, redirect=True)
        async def get(self):
            return {}