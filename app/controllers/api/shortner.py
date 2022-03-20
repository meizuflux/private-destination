import string
from app.routing import APIController, view
from app.utils.auth import requires_auth, AuthenticationScheme
from app.utils.db import Database
from aiohttp import web
from aiohttp_apispec import json_schema, match_info_schema
from marshmallow import Schema, fields
from secrets import choice
from asyncpg import UniqueViolationError

class CreateUrlSchema(Schema):
    key = fields.String()
    destination = fields.String()

class KeyMatchSchema(Schema):
    key = fields.String(required=True)

all_chars = string.ascii_letters + string.digits + "!@$%<>:+=-_~"

async def generate_url_key(db: Database):
    while True:
        key = "".join(choice(all_chars) for _ in range(5))
        if await db.check_short_url_exists(key) is False:
            break
    return key

class Shortner(APIController):
    @view()
    class Create(web.View):
        @requires_auth()
        @json_schema(CreateUrlSchema())
        async def post(self):
            req = self.request
            json = req["json"]
            key = json["key"]
            if key == "":
                key = await generate_url_key(req.app["db"])

            try:
                row = await self.request.app["db"].create_short_url(req["user"]["user_id"], key, json["destination"])
            except UniqueViolationError:
                return web.HTTPConflict(reason="already exists")
            return web.json_response({})

    @view("{key}")
    class Manipulate(web.View):
        @requires_auth()
        @match_info_schema(KeyMatchSchema)
        async def delete(self):
            req = self.request
            key = req["match_info"]["key"]

            await req.app["db"].delete_short_url(key)
            return web.json_response({"key": key})