from io import BytesIO
from json import dumps
from math import ceil

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from aiohttp_jinja2 import render_template_async, template
from asyncpg import UniqueViolationError
from marshmallow import ValidationError

from app.models.shortener import (
    ShortenerAliasSchema,
    ShortenerCreateSchema,
    ShortenerEditSchema,
    ShortenerFilterSchema,
)
from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.db import (
    delete_short_url,
    insert_short_url,
    select_short_url,
    select_short_urls_count,
    select_short_urls,
    update_short_url,
)
from app.utils.forms import parser
from app.utils.shortener import generate_url_alias

bp = Blueprint("/dashboard/shortener")


@bp.get("")
@requires_auth(redirect=True, scopes=["id", "admin"])
@querystring_schema(ShortenerFilterSchema())
@template("dashboard/shortener/index.html.jinja")
async def shortener(request: web.Request):
    current_page = request["querystring"].get("page", 1) - 1
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "creation_date")

    async with request.app["db"].acquire() as conn:
        urls = await select_short_urls(
            conn,
            sortby=sortby,
            direction=direction.upper(),
            owner=request["user"]["id"],
            offset=current_page * 50,
        )
        urls_count = await select_short_urls_count(conn, owner=request["user"]["id"])

    max_pages = ceil(urls_count / 50)

    if max_pages == 0:
        max_pages = 1
    return {
        "current_page": current_page + 1,
        "max_pages": max_pages,
        "values": urls,
        "sortby": sortby,
        "direction": direction,
    }


@bp.route("/create", methods=["GET", "POST"])
@requires_auth(redirect=True, scopes=["id", "admin"])
async def create_short_url_(request: web.Request) -> web.Response:
    if request.method == "POST":
        try:
            args = await parser.parse(ShortenerCreateSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/shortener/create.html.jinja",
                request,
                {
                    "alias_error": e.messages.get("alias"),
                    "url_error": e.messages.get("destination"),
                    "domain": f"https://{request.app['config']['domain']}/",
                    "alias": e.data.get("alias"),
                    "destination": e.data.get("destination"),
                },
                status=400,
            )

        alias = args.get("alias")
        if alias is None or alias == "":
            alias = await generate_url_alias(request.app["db"])
        destination = args.get("destination")

        try:
            await insert_short_url(request.app["db"], owner=request["user"]["id"], alias=alias, destination=destination)
        except UniqueViolationError:
            return await render_template_async(
                "dashboard/shortener/create.html.jinja",
                request,
                {
                    "alias_error": ["A shortened URL with this alias already exists"],
                    "domain": f"https://{request.app['config']['domain']}/",
                    "alias": alias,
                    "destination": destination,
                },
                status=400,
            )

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/create.html.jinja", request, {"domain": f"https://{request.app['config']['domain']}/"}
    )


@bp.route("/{alias}/edit", methods=["GET", "POST"])
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(ShortenerAliasSchema())
async def edit_short_url_(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]

    short_url = await select_short_url(request.app["db"], alias=alias)
    if short_url is None:
        return await render_template_async(
            "dashboard/shortener/edit.html.jinja",
            request,
            {
                "error": {"title": "Unknown Short URL", "message": "Could not locate short URL"},
                "domain": "https://{request.app['config']['domain']}/",
            },
        )

    if short_url["owner"] != request["user"]["id"]:
        return await render_template_async(
            "dashboard/shortener/edit.html.jinja",
            request,
            {
                "error": {"title": "Missing Permissions", "message": "You aren't the owner of this short URL"},
                "domain": "https://{request.app['config']['domain']}/",
            },
        )

    if request.method == "POST":
        try:
            args = await parser.parse(ShortenerEditSchema(), request, locations=["form"])
        except ValidationError as e:
            return await render_template_async(
                "dashboard/shortener/edit.html.jinja",
                request,
                {
                    "alias_error": e.messages.get("alias"),
                    "destination_error": e.messages.get("destination"),
                    "domain": f"https://{request.app['config']['domain']}/",
                    "alias": e.data.get("alias"),
                    "destination": e.data.get("destination"),
                },
                status=400,
            )

        new_alias = args.get("alias")
        if new_alias is None or new_alias == "":
            new_alias = await generate_url_alias(request.app["db"])
        destination = args["destination"]

        try:
            await update_short_url(
                request.app["db"],
                alias=alias,
                new_alias=new_alias,
                destination=destination,
                reset_clicks=args.get("reset_clicks", False),
            )
        except UniqueViolationError as e:
            return await render_template_async(
                "dashboard/shortener/edit.html.jinja",
                request,
                {
                    "alias_error": ["A shortened URL with this alias already exists"],
                    "alias": new_alias,
                    "destination": destination,
                    "clicks": None,
                    "domain": f"https://{request.app['config']['domain']}/",
                },
                status=400,
            )

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/edit.html.jinja",
        request,
        {
            "alias": short_url["alias"],
            "destination": short_url["destination"],
            "clicks": short_url["clicks"],
            "domain": f"https://{request.app['config']['domain']}/",
        },
    )


@bp.route("/{alias}/delete", methods=["GET", "POST"])
@requires_auth(redirect=True, scopes=["id", "admin"])
@match_info_schema(ShortenerAliasSchema)
async def delete_short_url_(request: web.Request) -> web.Response:
    alias = request["match_info"]["alias"]

    short_url = await select_short_url(request.app["db"], alias=alias)
    if short_url is None:
        return await render_template_async(
            "dashboard/shortener/delete.html.jinja",
            request,
            {"error": {"title": "Unknown Short URL", "message": "Could not locate short URL"}},
            status=404,
        )

    if short_url["owner"] != request["user"]["id"]:
        return await render_template_async(
            "dashboard/shortener/delete.html.jinja",
            request,
            {"error": {"title": "Missing Permissions", "message": "You aren't the owner of this short URL"}},
            status=409,
        )

    if request.method == "POST":
        await delete_short_url(request.app["db"], alias=alias)

        return web.HTTPFound("/dashboard/shortener")

    return await render_template_async(
        "dashboard/shortener/delete.html.jinja",
        request,
        {"alias": short_url["alias"], "destination": short_url["destination"], "clicks": short_url["clicks"]},
    )


@bp.get("/sharex")
@requires_auth(redirect=False, scopes=["api_key"])
async def shortener_sharex_config(request: web.Request) -> web.Response:
    data = {
        "Version": "13.4.0",
        "DestinationType": "URLShortener",
        "RequestMethod": "POST",
        "RequestURL": "https://mzf.one/api/shortener",
        "Headers": {"x-api-key": request["user"]["api_key"]},
        "Body": "JSON",
        "Data": '{"destination":"$input$"}',
        "URL": "https://mzf.one/$json:alias$",
        "ErrorMessage": "$json:message$",
    }

    return web.Response(
        body=BytesIO(dumps(data).encode("utf-8")).getbuffer(),
        headers={"Content-Disposition": 'attachment; filename="mzf.one.sxcu"'},
    )
