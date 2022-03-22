from aiohttp_apispec import querystring_schema
import aiohttp_jinja2
from app.routing import Controller, view
from aiohttp import web

from app.utils.auth import requires_auth
from marshmallow import Schema, fields, validate

class ShortnerQuerystring(Schema):
    page = fields.Integer(required=False)
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"key", "destination", "clicks", "creation_date"}))

class UsersQuerystring(Schema):
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"username", "user_id", "authorized", "oauth_provider", "joined"}))

class Dashboard(Controller):
    @view()
    class Index(web.View):
        @requires_auth(redirect=True, scopes=["user_id", "username", "admin"])
        @aiohttp_jinja2.template("dashboard/dashboard.html")
        async def get(self):
            urls = await self.request.app["db"].get_short_url_count(self.request["user"]["user_id"])
            return {"url_count": urls}

    @view("shortner")
    class Shortner(web.View):
        @requires_auth(redirect=True, scopes=["user_id", "admin"])
        @querystring_schema(ShortnerQuerystring)
        @aiohttp_jinja2.template("dashboard/shortner.html")
        async def get(self):
            current_page = self.request["querystring"].get("page", 1) - 1
            direction = self.request["querystring"].get("direction", "desc")
            sortby = self.request["querystring"].get("sortby", "creation_date")

            urls = await self.request.app["db"].get_short_urls(
                sortby=sortby.lower(),
                direction=direction.upper(),
                owner=self.request["user"]["user_id"],
                offset=current_page * 50
            )
            max_pages = await self.request.app["db"].get_short_url_max_pages(self.request["user"]["user_id"])

            if max_pages == 0:
                max_pages = 1
            return {
                "current_page": current_page + 1,
                "max_pages": max_pages,
                "values": urls,
            }

    @view("settings")
    class Settings(web.View):
        @aiohttp_jinja2.template("dashboard/settings.html")
        @requires_auth(redirect=True, scopes=["api_key", "oauth_provider", "username", "admin"])
        async def get(self):
            return {}

    @view("users")
    class Users(web.View):
        @aiohttp_jinja2.template("dashboard/users.html")
        @querystring_schema(UsersQuerystring)
        @requires_auth(admin=True, redirect=True)
        async def get(self):
            direction = self.request["querystring"].get("direction", "desc")
            sortby = self.request["querystring"].get("sortby", "joined")

            users = await self.request.app["db"].get_users(sortby, direction)
            return {"users": users}