import string
from secrets import choice

from aiohttp import web
from aiohttp_apispec import json_schema, match_info_schema
from asyncpg import UniqueViolationError

from app.models.shortener import ShortenerCreateSchema, ShortenerAliasSchema
from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.db import (
    ConnOrPool,
    delete_short_url,
    insert_short_url,
    select_short_url_exists,
)

all_chars = string.ascii_letters + string.digits


async def generate_url_alias(conn: ConnOrPool):
    while True:
        alias = "".join(choice(all_chars) for _ in range(7))
        if await select_short_url_exists(conn, alias=alias) is False:
            break
    return alias


bp = Blueprint("/api/shortener")


@bp.post("")
@requires_auth(scopes="id")
@json_schema(ShortenerCreateSchema())
async def create_short_url_(request: web.Request) -> web.Response:
    json = request["json"]
    alias = json.get("alias")
    if alias is None or alias == "":
        alias = await generate_url_alias(request.app["db"])

    try:
        await insert_short_url(request.app["db"], owner=request["user"]["id"], alias=alias, destination=json["destination"])
    except UniqueViolationError:
        return web.json_response({"message": "A shortened url with this alias already exists"}, status=409)
    return web.json_response({"alias": alias, "destination": json["destination"]})


@bp.delete("/{alias}")
@requires_auth(scopes=None)
@match_info_schema(ShortenerAliasSchema())
async def delete_short_url_(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]

    await delete_short_url(request.app["db"], alias=alias)
    return web.json_response({"alias": alias})
