from secrets import token_urlsafe
from urllib.parse import quote
from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, querystring_schema
from app.routing import APIController, view
from marshmallow import Schema, fields, validate

from app.utils.auth.providers import providers

class ProviderQuery(Schema):
    provider = fields.Str(required=True, validate=validate.OneOf(providers.keys()))

class CallbackQuerystring(Schema):
    code = fields.Str(required=True)
    state = fields.Str()

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

            await app["db"].create_user(user, p)
            uuid = await app["db"].create_session(user["id"])
            print(uuid)
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
        async def get(self):
            res = web.json_response({"message": "Logged out"})
            res.del_cookie("_session")
            return res

    @view("providers")
    class Providers(web.View):
        async def get(self):
            providers = []
            for key, provider in self.request.app["oauth_providers"].items():
                providers.append({"key": key, "name": provider.name})

            return web.json_response(providers)
