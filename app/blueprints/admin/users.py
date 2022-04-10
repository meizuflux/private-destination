from aiohttp_apispec import match_info_schema, querystring_schema
from aiohttp_jinja2 import render_template_async, template
from app.models.auth import UserIDSchema, UsersFilterSchema
from app.routing import Blueprint
from app.utils import Status
from app.utils.auth import create_user, edit_user, requires_auth
from app.utils.db import delete_user, select_user, select_users
from aiohttp import web


bp = Blueprint("/admin/users")

@bp.get("")
@template("dashboard/users/index.html")
@querystring_schema(UsersFilterSchema())
@requires_auth(admin=True, redirect=True)
async def users(request: web.Request):
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "joined")

    users = await select_users(request.app["db"], sortby=sortby, direction=direction)
    return {"users": users, "sortby": sortby, "direction": direction}


@bp.get("/{user_id}/edit")
@bp.post("/{user_id}/edit")
@match_info_schema(UserIDSchema)
@requires_auth(admin=True, redirect=True, scopes="id", needs_authorization=False)
async def edit_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]
    user = await select_user(request.app["db"], user_id=user_id)
    is_self = user_id == request["user"]["id"]

    if user is None:
        return await render_template_async(
            "dashboard/users/edit.html",
            request,
            {"error": {"title": "Unknown User", "message": "Could not locate user"}},
            status=404,
        )

    if request.method == "POST":
        status, ret = await edit_user(
            request,
            old_user=user,
            template="dashboard/users/edit.html",
            extra_ctx={
                "is_self": is_self,
            }
        )
        if status is Status.ERROR:
            return ret

        return web.HTTPFound("/dashboard/users")

    return await render_template_async(
        "dashboard/users/edit.html",
        request,
        {
            "id": user["id"],
            "email": user["email"],
            "authorized": user["authorized"],
            "admin": user["admin"],
            "joined": user["joined"],
            "is_self": is_self,
        },
    )


@bp.get("/{user_id}/delete")
@bp.post("/{user_id}/delete")
@requires_auth(redirect=True, scopes=["id", "admin"], needs_authorization=False)
@match_info_schema(UserIDSchema)
async def delete_user_(request: web.Request) -> web.Response:
    user_id = request["match_info"]["user_id"]
    user = await select_user(request.app["db"], user_id=user_id)

    if user is None:
        return await render_template_async(
            "dashboard/users/delete.html",
            request,
            {"error": {"title": "Unknown User", "message": "Could not locate user"}},
            status=404,
        )

    if request.method == "POST":
        await delete_user(request.app["db"], user_id=user_id)

        return web.HTTPFound("/dashboard/users")

    return await render_template_async(
        "dashboard/users/delete.html",
        request,
        {"id": user["id"], "email": user["email"]},
    )


@bp.get("/create")
@bp.post("/create")
@requires_auth(admin=True, redirect=True)
async def create_user_(request: web.Request) -> web.Response:
    if request.method == "POST":
        status, ret = await create_user(request, template="onboarding.html", extra_ctx={"type": "signup"})
        if status is Status.ERROR:
            return ret

        return web.HTTPFound("/dashboard/users")

    return await render_template_async("dashboard/users/create.html", request, {})