from urllib.parse import quote
from blacksheep import Request, Response, auth
from blacksheep.cookies import Cookie
from blacksheep.server.controllers import ApiController, get

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

        request.session["provider"] = p

        url = provider.urls.authorization.url
        url += f"?redirect_uri={self.app.config['callback_url'] + f'/{p}'}&client_id={provider.credentials.client_id}"
        print(url)

        for k, v in provider.urls.authorization.params.items():
            url += f"&{k}={quote(v)}"


        if provider.urls.authorization.state is True:
            state = token_urlsafe(32)
            
            request.session["state"] = state
            url += "&state=" + state

        return self.temporary_redirect(url)

    @get("callback/{provider}")
    async def tcallback(self, request: Request, provider: str, code: str, state: str = None) -> Response:
        p = provider
        provider = self.app.oauth_providers.get(provider)
        if provider is None:
            return self.json({"message": "oauth provider not found"}, 400)

        if provider.urls.authorization.state == True:
            if state != request.session.get("state"):
                return self.text("state doesn't match")

        del request.session["state"]

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

        request.session["user"] = user

        return self.json(user)

    @get("providers")
    async def providers(self) -> Response:
        return self.json(list(self.app.oauth_providers.keys()))

    @auth()
    @get("logout")
    async def logout(self, request: Request) -> Response:
        request.session.clear()
        return self.json({"message": "logged out"})