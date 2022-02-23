from urllib.parse import quote
from blacksheep import Request, Response
from blacksheep.server.controllers import ApiController, get

from app.utils.app import CustomApplication
from secrets import token_urlsafe

class Auth(ApiController):
    def __init__(self, app: CustomApplication):
        self.app = app

    @get("login")
    async def login(self, request: Request, found_provider: str) -> Response:
        found_provider = self.app.oauth_providers.get(found_provider)

        if found_provider is None:
            return self.json({"message": "oauth provider not found"}, 400)

        request.session["provider"] = found_provider

        url = found_provider["urls"]["authorization"]["url"]

        for i, (k, v) in enumerate(found_provider["urls"]["authorization"]["params"].items()):
            url += f"{'?' if i == 0 else '&'}{k}={quote(v)}"

        if found_provider["urls"]["authorization"]["state"] is True:
            state = token_urlsafe(32)
            
            request.session["state"] = state
            url += "&state=" + state

        print(url)

        return self.temporary_redirect(url)

    @get("callback")
    async def tcallback(self, request: Request, code: str, state: str = None) -> Response:
        provider = self.app.oauth_providers.get(request.session.get("provider"))
        if provider["urls"]["authorization"]["state"] == True:
            if state != request.session.get("state"):
                return self.text("state doesn't match")

        del request.session["state"]

        body = {

        }

        async with self.app.session.get(provider["urls"]["token"], body=body, headers={"Content-Type": "application/x-www-form-urlencoded"}):
            ...

        return self.text("logged in")