from aiohttp import web
from aiohttp_apispec import match_info_schema
from marshmallow import Schema, fields

from app.blueprints.auth import generate_api_key
from app.routing import Blueprint
from app.utils.auth import requires_auth


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
    await request.app["db"].update_api_key(request["user"]["id"], new_api_key)
    return web.json_response({"api_key": new_api_key})


@bp.post("/{user_id}/authorize")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def authorize_user(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await request.app["db"].authorize_user(user_id)

    return web.json_response({"message": "user authorized"})


@bp.post("/{user_id}/unauthorize")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def unauthorize_user(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await request.app["db"].unauthorize_user(user_id)

    return web.json_response({"message": "user unauthorized"})


@bp.delete("/{user_id}/delete")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def delete_user(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await request.app["db"].delete_user(user_id)

    return web.json_response({"message": "user deleted"})
