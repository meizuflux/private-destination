import json
from secrets import token_urlsafe
from urllib.parse import quote
from uuid import UUID
from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from app.routing import APIController, view
from marshmallow import Schema, fields, validate
from app.utils.auth import AuthenticationScheme, requires_auth

from app.utils.auth.providers import providers
from ua_parser import user_agent_parser

import string
from secrets import choice

from app.utils.db import Database

class ProviderQuery(Schema):
    provider = fields.Str(required=True, validate=validate.OneOf(providers.keys()))

class CallbackQuerystring(Schema):
    code = fields.Str(required=True)
    state = fields.Str()

all_chars = string.ascii_letters + string.digits + "!@#$%^&?<>:;+=-_~"

async def generate_api_key(db: Database):
    while True:
        key = "".join(choice(all_chars) for _ in range(128))
        if await db.validate_api_key(key) is False:
            break
    return key

class Auth(APIController):
    @view("login")
    class Login(web.View):
        @querystring_schema(ProviderQuery)
        async def get(self):
            request = self.request
            app = self.request.app
            p = request["querystring"]["provider"]
            provider = app["oauth_providers"].get(p)

            if provider is None:
                return web.json_response({"message": "oauth provider not found"}, status=400)


            url = provider.urls.authorization.url
            url += f"?redirect_uri={app['config']['callback_url'] + f'/{p}'}&client_id={provider.credentials.client_id}"
            print(url)

            for k, v in provider.urls.authorization.params.items():
                url += f"&{k}={quote(v)}"

            state = None
            if provider.urls.authorization.state is True:
                state = token_urlsafe(32)
                url += "&state=" + state

            res = web.HTTPTemporaryRedirect(url)
            res.set_cookie(
                "state",
                state,
                max_age=60 * 5,
                httponly=True,
                secure=not app["dev"]
            )
            if request.cookies.get("_session") is not None:
                res.del_cookie("_session")

            return res

    @view("callback/{provider}")
    class Callback(web.View):
        @match_info_schema(ProviderQuery)
        @querystring_schema(CallbackQuerystring)
        async def get(self):
            request = self.request
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
                'grant_type': 'authorization_code',
                "redirect_uri": app["config"]["callback_url"] + "/" + p
            }

            async with app["session"].post(provider.urls.token, data=body, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}) as req:
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
            res.set_cookie(
                "_session",
                str(uuid),
                max_age=60 * 60 * 24,
                httponly=True,
                secure=not app["dev"]
            )

            return res

    @view("logout")
    class Logout(web.View):
        @requires_auth(scheme=AuthenticationScheme.SESSION, wants_user_info=False)
        async def get(self):
            token = self.request.cookies.get("_session")
            res = web.HTTPTemporaryRedirect("/login")
            res.del_cookie("_session")
            await self.request.app["db"].delete_session(UUID(token))
            return res

    @view("providers")
    class Providers(web.View):
        async def get(self):
            providers = []
            for key, provider in self.request.app["oauth_providers"].items():
                providers.append({"key": key, "name": provider.name})

            return web.json_response(providers)

    @view("api_key")
    class APIKey(web.View):
        @requires_auth()
        async def post(self):
            api_key = await generate_api_key(self.request.app["db"])
            await self.request.app["db"].regenerate_api_key(self.request["user"]["user_id"], api_key)
            return web.json_response({"api_key": api_key})

    @view("@me")
    class Me(web.View):
        @requires_auth()
        async def get(self):
            request = self.request
            user = request["user"]
            data = {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "avatar_url": user["avatar_url"],
                "api_key": user["api_key"],
                "oauth_provider": user["oauth_provider"],
                "joined": user["joined"].isoformat()
            }

            return web.json_response(data)