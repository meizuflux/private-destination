from urllib.parse import quote
from blacksheep import Request, Response
from blacksheep.cookies import Cookie
from blacksheep.server.controllers import ApiController, get

from app.utils.app import CustomApplication
from secrets import token_urlsafe

class Auth(ApiController):
    def __init__(self, app: CustomApplication):
        self.app = app

    @get("login")
    async def login(self, request: Request, provider: str) -> Response:
        found_provider = self.app.oauth_providers.get(provider)

        if found_provider is None:
            return self.json({"message": "oauth provider not found"}, 400)

        request.session["provider"] = provider

        url = found_provider.urls.authorization.url
        url += f"?redirect_uri={quote(self.app.config['callback_url'] + f'/{provider}')}&client_id={found_provider.credentials.client_id}"

        for k, v in found_provider.urls.authorization.params.items():
            url += f"&{k}={quote(v)}"


        if found_provider.urls.authorization.state is True:
            state = token_urlsafe(32)
            
            request.session["state"] = state
            url += "&state=" + state

        print(request.session._values)
        return self.temporary_redirect(url)

    @get("callback/{provider}")
    async def tcallback(self, request: Request, provider: str, code: str, state: str = None) -> Response:
        found_provider = self.app.oauth_providers.get(provider)
        if found_provider is None:
            return self.json({"message": "oauth provider not found"}, 400)

        if not self.app.IS_DEV:
            if found_provider.urls.authorization.state == True:
                if state != request.session.get("state"):
                    return self.text("state doesn't match")

        #del request.session["state"]

        body = {
            "client_id": found_provider.credentials.client_id,
            "client_secret": found_provider.credentials.client_secret,
            "code": code,
            "redirect_uri": self.app.config["callback_url"] + "/" + provider
        }

        async with self.app.session.get(found_provider.urls.token, data=body, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}) as req:
            data = await req.json()

        async with self.app.session.get(found_provider.urls.user, headers={"Authorization": "Bearer " + data["access_token"]}) as req:
            raw = await req.json()

        user = found_provider.parse_data(raw)

        return self.json(user)