import json
from secrets import token_urlsafe
from urllib.parse import quote
from uuid import UUID
from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from app.routing import APIController, view
from marshmallow import Schema, fields, validate
from app.utils.auth import requires_auth


class UserIdMatchinfo(Schema):
    user_id = fields.Integer()

class Users(APIController):
    @view("me")
    class Me(web.View):
        @requires_auth(scopes="*")
        async def get(self):
            user = self.request["user"]

            return web.json_response({
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "avatar_url": user["avatar_url"],
                "api_key": user["api_key"],
                "oauth_provider": user["oauth_provider"],
                "joined": user["joined"].isoformat(),
                "authorized": user["authorized"],
                "admin": user["admin"]
            })

    @view("{user_id}/authorize")
    class Authorize(web.View):
        @requires_auth(admin=True)
        @match_info_schema(UserIdMatchinfo)
        async def get(self):
            user_id = self.request["match_info"]["user_id"]

            await self.request.app["db"].execute("UPDATE users SET authorized = true WHERE user_id = $1", user_id)

            return web.json_response({"message": "user authorized"})

    @view("{user_id}/delete")
    class Deny(web.View):
        @requires_auth(admin=True)
        @match_info_schema(UserIdMatchinfo)
        async def get(self):
            user_id = self.request["match_info"]["user_id"]

            await self.request.app["db"].execute("DELETE FROM users WHERE user_id = $1", user_id)

            return web.json_response({"message": "user deleted"})