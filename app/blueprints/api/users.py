from aiohttp import web
from aiohttp_apispec import match_info_schema
from marshmallow import Schema, fields

from app.utils.auth import generate_api_key
from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.db import authorize_user, delete_user, unauthorize_user, update_api_key


class UserIdMatchinfo(Schema):
    user_id = fields.Integer()


bp = Blueprint("/api/users")


@bp.get("/me")
@requires_auth(scopes="*")
async def me(request: web.Request) -> web.Response:
    user = request["user"]

    return web.json_response(
        {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "api_key": user["api_key"],
            "joined": user["joined"].isoformat(),
            "authorized": user["authorized"],
            "admin": user["admin"],
        }
    )


@bp.post("/me/api_key")
@requires_auth(scopes="id")
async def regen_api_key(request: web.Request) -> web.Response:
    new_api_key = await generate_api_key(request.app["db"])
    await update_api_key(request.app["db"], user_id=request["user"]["id"], api_key=new_api_key)
    return web.json_response({"api_key": new_api_key})


@bp.post("/{user_id}/authorize")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def authorize_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await authorize_user(request.app["db"], user_id=user_id)

    return web.json_response({"message": "user authorized"})


@bp.post("/{user_id}/unauthorize")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def unauthorize_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await unauthorize_user(request.app["db"], user_id=user_id)

    return web.json_response({"message": "user unauthorized"})


@bp.delete("/{user_id}/delete")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def delete_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await delete_user(request.app["db"], user_id=user_id)

    return web.json_response({"message": "user deleted"})
