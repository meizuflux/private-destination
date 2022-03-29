from aiohttp import web
from aiohttp_apispec import match_info_schema
from marshmallow import Schema, fields

from app.routing import Blueprint
from app.utils.auth import requires_auth


class UserIdMatchinfo(Schema):
    user_id = fields.Integer()


bp = Blueprint("/api/users")


@bp.get("/me")
@requires_auth(scopes="*")
async def get(request: web.Request) -> web.Response:
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


@bp.get("/{user_id}/authorize")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def get(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await request.app["db"].execute("UPDATE users SET authorized = true WHERE id = $1", user_id)

    return web.json_response({"message": "user authorized"})


@bp.get("/{user_id}/unauthorize")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def get(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await request.app["db"].execute("UPDATE users SET authorized = false WHERE id = $1", user_id)

    return web.json_response({"message": "user unauthorized"})


@bp.get("/{user_id}/delete")
@requires_auth(admin=True)
@match_info_schema(UserIdMatchinfo)
async def get(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]

    await request.app["db"].execute("DELETE FROM users WHERE id = $1", user_id)

    return web.json_response({"message": "user deleted"})