import string
from secrets import choice

from aiohttp import web
from aiohttp_apispec import json_schema, match_info_schema
from asyncpg import UniqueViolationError
from marshmallow import Schema, fields

from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.db import ConnOrPool, insert_short_url, delete_short_url


class CreateUrlSchema(Schema):
    key = fields.String()
    destination = fields.URL(required=True, schemes={"http", "https"})


class KeyMatchSchema(Schema):
    key = fields.String(required=True)


all_chars = string.ascii_letters + string.digits


async def generate_url_key(conn: ConnOrPool):
    while True:
        key = "".join(choice(all_chars) for _ in range(7))
        if await conn.check_short_url_exists(key) is False:
            break
    return key


bp = Blueprint("/api/shortner")


@bp.post("")
@requires_auth(scopes="id")
@json_schema(CreateUrlSchema())
async def create_short_url_(request: web.Request) -> web.Response:
    json = request["json"]
    key = json.get("key")
    if key is None or key == "":
        key = await generate_url_key(request.app["db"])

    try:
        await insert_short_url(
            request.app["db"],
            owner=request["user"]["id"],
            key=key,
            destination=json["destination"]
        )
    except UniqueViolationError:
        return web.json_response({"message": "A shortened url with this key already exists"}, status=409)
    return web.json_response({"key": key, "destination": json["destination"]})


@bp.delete("/{key}")
@requires_auth(scopes=None)
@match_info_schema(KeyMatchSchema)
async def delete_short_url_(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]

    await delete_short_url(
        request.app["db"],
        key=key
    )
    return web.json_response({"key": key})
