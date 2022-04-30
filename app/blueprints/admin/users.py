from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema

from app.models.auth import UserIDSchema, UsersFilterSchema
from app.routing import Blueprint
from app.templating import render_template
from app.utils import Status
from app.utils.auth import create_user, edit_user, requires_auth
from app.utils.db import delete_user, select_user, select_users
from app.utils.time import get_amount_and_unit

bp = Blueprint("/admin/users", name="users")


@bp.get("", name="index")
@querystring_schema(UsersFilterSchema())
@requires_auth(admin=True, redirect=True)
async def list_users(request: web.Request) -> web.Response:
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "joined")

    users = await select_users(request.app["db"], sortby=sortby, direction=direction)
    return await render_template(
        "admin/users/index", request, {"users": users, "sortby": sortby, "direction": direction}
    )


@bp.route("/{user_id}/edit", methods=["GET", "POST"], name="edit")
@match_info_schema(UserIDSchema)
@requires_auth(admin=True, redirect=True, scopes="id")
async def edit_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]
    user = await select_user(request.app["db"], user_id=user_id)
    is_self = user_id == request["user"]["id"]

    if user is None:
        return await render_template(
            "admin/users/edit",
            request,
            {"error": {"title": "Unknown User", "message": "Could not locate user"}},
            status=404,
        )

    session_duration = get_amount_and_unit(user["session_duration"])

    if request.method == "POST":
        ret = await edit_user(
            request,
            old_user=user,
            session_duration=session_duration,
            template="admin/users/edit",
            extra_ctx={
                "is_self": is_self,
            },
        )
        if ret[0] is Status.ERROR:
            return ret[1]

        return web.HTTPFound("/admin/users")

    return await render_template(
        "admin/users/edit",
        request,
        {
            "id": user["id"],
            "email": user["email"],
            "admin": user["admin"],
            "joined": user["joined"],
            "is_self": is_self,
        },
    )


@bp.route("/{user_id}/delete", methods=["GET", "POST"], name="delete")
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(UserIDSchema)
async def delete_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]
    user = await select_user(request.app["db"], user_id=user_id)

    if user is None:
        return await render_template(
            "admin/users/delete",
            request,
            {"error": {"title": "Unknown User", "message": "Could not locate user"}},
            status=404,
        )

    if request.method == "POST":
        await delete_user(request.app["db"], user_id=user_id)

        return web.HTTPFound("/admin/users")

    return await render_template(
        "admin/users/delete",
        request,
        {"id": user["id"], "email": user["email"]},
    )


@bp.route("/create", methods=["GET", "POST"], name="create")
@requires_auth(admin=True, redirect=True)
async def create_user_(request: web.Request) -> web.Response:
    if request.method == "POST":
        ret = await create_user(request, template="onboarding", extra_ctx={"type": "signup"})
        if ret[0] is Status.ERROR:
            return ret[1]

        return web.HTTPFound("/admin/users")

    return await render_template("admin/users/create", request)
