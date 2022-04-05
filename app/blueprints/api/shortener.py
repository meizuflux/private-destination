import string
from secrets import choice

from aiohttp import web
from aiohttp_apispec import json_schema, match_info_schema
from asyncpg import UniqueViolationError

from app.models.shortener import ShortenerCreateSchema, ShortenerKeySchema
from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.db import (
    ConnOrPool,
    delete_short_url,
    insert_short_url,
    select_short_url_exists,
)

all_chars = string.ascii_letters + string.digits


async def generate_url_key(conn: ConnOrPool):
    while True:
        key = "".join(choice(all_chars) for _ in range(7))
        if await select_short_url_exists(conn, key=key) is False:
            break
    return key


bp = Blueprint("/api/shortener")


@bp.post("")
@requires_auth(scopes="id")
@json_schema(ShortenerCreateSchema())
async def create_short_url_(request: web.Request) -> web.Response:
    json = request["json"]
    key = json.get("key")
    if key is None or key == "":
        key = await generate_url_key(request.app["db"])

    try:
        await insert_short_url(request.app["db"], owner=request["user"]["id"], key=key, destination=json["destination"])
    except UniqueViolationError:
        return web.json_response({"message": "A shortened url with this key already exists"}, status=409)
    return web.json_response({"key": key, "destination": json["destination"]})


@bp.delete("/{key}")
@requires_auth(scopes=None)
@match_info_schema(ShortenerKeySchema())
async def delete_short_url_(request: web.Request) -> web.Response:
    key = request["match_info"]["key"]

    await delete_short_url(request.app["db"], key=key)
    return web.json_response({"key": key})
