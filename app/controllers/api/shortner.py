from app.routing import APIController, view
from app.utils.auth import requires_auth, AuthenticationScheme
from app.utils.db import Database
from aiohttp import web
from aiohttp_apispec import json_schema
from marshmallow import Schema, fields
from .auth import all_chars
from secrets import choice

class CreateUrlSchema(Schema):
    key = fields.String()
    destination = fields.String()

async def generate_url_key(db: Database):
    while True:
        key = "".join(choice(all_chars) for _ in range(5))
        if await db.fetchval("SELECT EXISTS(SELECT 1 FROM urls WHERE key = $1)", key) is False:
            break
    return key

class Shortner(APIController):
    @view()
    class Operations(web.View):
        @requires_auth()
        @json_schema(CreateUrlSchema())
        async def post(self):
            req = self.request
            json = req["json"]
            key = json["key"]
            if key == "":
                key = await generate_url_key(req.app["db"])

            row = await self.request.app["db"].create_short_url(req["user"]["user_id"], key, json["destination"])
            return web.json_response({})