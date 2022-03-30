import string
from secrets import choice

from aiohttp import web
from aiohttp_apispec import json_schema, match_info_schema
from asyncpg import UniqueViolationError
from marshmallow import Schema, fields

from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.db import Database


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


bp = Blueprint("/api/shortner")


@bp.post("")
@requires_auth(scopes="id")
@json_schema(CreateUrlSchema())
async def create_short_url(request: web.Request) -> web.Response:
    json = request["json"]
    key = json.get("key")
    if key is None or key == "":
        key = await generate_url_key(request.app["db"])

    try:
        await request.app["db"].create_short_url(request["user"]["id"], key, json["destination"])
    except UniqueViolationError:
        return web.HTTPConflict(reason="already exists")
    return web.json_response({"key": key, "destination": json["destination"]})


@bp.delete("/{key}")
@requires_auth(scopes=None)
@match_info_schema(KeyMatchSchema)
async def delete_short_url(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]

    await request.app["db"].delete_short_url(key)
    return web.json_response({"key": key})
