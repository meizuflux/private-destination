import string
from secrets import choice, token_urlsafe
from urllib.parse import quote
from uuid import UUID

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from marshmallow import Schema, fields, validate
from ua_parser import user_agent_parser

from app.routing import Blueprint
from app.utils.auth import requires_auth
from app.utils.auth.providers import providers
from app.utils.db import Database


class ProviderQuery(Schema):
    provider = fields.Str(required=True, validate=validate.OneOf(providers.keys()))


class CallbackQuerystring(Schema):
    code = fields.Str(required=True)
    state = fields.Str()


class DeleteQuerystring(Schema):
    redirect = fields.Boolean(truthy={"True"}, falsy={"False"})


all_chars = string.ascii_letters + string.digits + "!@$%^&?<>:;+=-_~"


async def generate_api_key(db: Database):
    while True:
        key = "".join(choice(all_chars) for _ in range(128))
        if await db.validate_api_key(key) is False:
            break
    return key


bp = Blueprint("/api/auth")


@bp.get("/login")
@querystring_schema(ProviderQuery)
async def login(request: web.Request) -> web.Response:
    app = request.app
    p = request["querystring"]["provider"]
    provider = app["oauth_providers"].get(p)

    if provider is None:
        return web.json_response({"message": "oauth provider not found"}, status=400)

    url = provider.urls.authorization.url
    url += f"?redirect_uri={app['config']['callback_url'] + f'/{p}'}&client_id={provider.credentials.client_id}"

    for k, v in provider.urls.authorization.params.items():
        url += f"&{k}={quote(v)}"

    state = ""
    if provider.urls.authorization.state is True:
        state = token_urlsafe(32)
        url += "&state=" + state

    res = web.HTTPFound(url)
    res.set_cookie("state", state, max_age=60 * 5, httponly=True, secure=not app["dev"])
    if request.cookies.get("_session") is not None:
        res.del_cookie("_session")

    return res


@bp.get("/callback/{provider}")
@match_info_schema(ProviderQuery)
@querystring_schema(CallbackQuerystring)
async def oauth_callback(request: web.Request) -> web.Response:
    app = request.app

    p = request["match_info"]["provider"]
    provider = app["oauth_providers"].get(p)
    if provider is None:
        return web.json_response({"message": "oauth provider not found"}, status=400)

    state = request["querystring"]["state"]
    code = request["querystring"]["code"]

    if provider.urls.authorization.state == True:
        if state != request.cookies.get("state"):
            return web.json_response({"message": "state doesnt match"}, status=400)

    res = web.HTTPFound("/")
    res.del_cookie("state")

    body = {
        "client_id": provider.credentials.client_id,
        "client_secret": provider.credentials.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": app["config"]["callback_url"] + "/" + p,
    }

    async with app["session"].post(
        provider.urls.token,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    ) as req:
        if req.status != 200:
            return web.json_response({"message": "Failed to fetch token"}, status=500)
        data = await req.json()
        access_token = data.get("access_token")
        if access_token is None:
            return web.json_response({"message": "Failed to fetch token"}, status=500)

    async with app["session"].get(provider.urls.user, headers={"Authorization": "Bearer " + access_token}) as req:
        raw = await req.json()

    user = provider.parse_data(raw)
    user["api_key"] = await generate_api_key(app["db"])

    metadata = user_agent_parser.Parse(request.headers.getone("User-Agent"))
    browser = metadata["user_agent"]["family"].replace("Other", "Unknown")
    os = metadata["os"]["family"].replace("Other", "UnknownOS")

    await app["db"].create_user(user, p)
    uuid = await app["db"].create_session(user["id"], browser=browser, os=os)
    res.set_cookie("_session", str(uuid), max_age=60 * 60 * 24, httponly=True, secure=not app["dev"])

    return res


@bp.get("/logout")
@requires_auth()
async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get("_session")
    res = web.HTTPFound("/login")
    res.del_cookie("_session")
    await request.app["db"].delete_session(UUID(token))
    return res


@bp.get("/providers")
async def list_providers(request: web.Request) -> web.Response:
    providers = []
    for key, provider in request.app["oauth_providers"].items():
        providers.append({"key": key, "name": provider.name})

    return web.json_response(providers)


@bp.post("/api_key")
@requires_auth(scopes="user_id")
async def regen_api_key(request: web.Request) -> web.Response:
    api_key = await generate_api_key(request.app["db"])
    await request.app["db"].regenerate_api_key(request["user"]["user_id"], api_key)
    return web.json_response({"api_key": api_key})


@bp.get("/delete")
@requires_auth(scopes="user_id")
@querystring_schema(DeleteQuerystring)
async def delete_account(request: web.Request) -> web.Response:
    await request.app["db"].delete_user(request["user"]["user_id"])

    if request["querystring"].get("redirect") is True:
        return web.HTTPFound("/")
    return web.json_response({"message": "account deleted"})
