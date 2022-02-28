from datetime import datetime, timedelta
from urllib.parse import quote
from blacksheep import Request, Response, auth
from blacksheep.cookies import Cookie
from blacksheep.server.controllers import ApiController, get
from guardpost import Identity

from app.utils.app import CustomApplication
from secrets import token_urlsafe

class Auth(ApiController):
    def __init__(self, app: CustomApplication):
        self.app = app

    @get("login")
    async def login(self, request: Request, provider: str) -> Response:
        

        p = provider
        provider = self.app.oauth_providers.get(provider)

        if provider is None:
            return self.json({"message": "oauth provider not found"}, 400)

        

        url = provider.urls.authorization.url
        url += f"?redirect_uri={self.app.config['callback_url'] + f'/{p}'}&client_id={provider.credentials.client_id}"
        print(url)

        

        for k, v in provider.urls.authorization.params.items():
            url += f"&{k}={quote(v)}"

        state = None
        if provider.urls.authorization.state is True:
            state = token_urlsafe(32)
            
            
            url += "&state=" + state

        res = self.temporary_redirect(url)
        res.set_cookie(
            Cookie(
                "state",
                state
            )
        )
        if request.get_cookie("id") is not None:
            res.remove_cookie("id")

        return res

    @get("callback/{provider}")
    async def tcallback(self, request: Request, provider: str, code: str, state: str = None) -> Response:
        p = provider
        provider = self.app.oauth_providers.get(provider)
        if provider is None:
            return self.json({"message": "oauth provider not found"}, 400)

        if provider.urls.authorization.state == True:
            if state != request.get_cookie("state"):
                return self.text("state doesn't match")

        res = self.redirect("/")
        res.remove_cookie("state")

        body = {
            "client_id": provider.credentials.client_id,
            "client_secret": provider.credentials.client_secret,
            "code": code,
            'grant_type': 'authorization_code',
            "redirect_uri": self.app.config["callback_url"] + "/" + p
        }

        async with self.app.session.post(provider.urls.token, data=body, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}) as req:
            if req.status != 200:
                return self.json({"message": "Failed to fetch token"}, 500)
            data = await req.json()

        async with self.app.session.get(provider.urls.user, headers={"Authorization": "Bearer " + data["access_token"]}) as req:
            raw = await req.json()

        user = provider.parse_data(raw)

        await self.app.db.create_user(user, p)
        uuid = await self.app.db.create_session(user["id"])
        print(uuid)
        res.set_cookie(
            Cookie(
                "id",
                str(uuid),
                datetime.now() + timedelta(days=1),
                path="/",
                http_only=True,
                secure=not self.app.IS_DEV
            )
        )

        return res

    @get("providers")
    async def providers(self) -> Response:
        providers = []
        for key, provider in self.app.oauth_providers.items():
            providers.append({"key": key, "name": provider.name})

        return self.json(providers)

    @auth()
    @get("logout")
    async def logout(self, request: Request) -> Response:
        res = self.json({"message": "logged out"})
        res.remove_cookie("id")
        return res

    @auth()
    @get("@me")
    async def me(self, user: Identity) -> Response:
        return self.json(user.claims)