from datetime import timezone
from blacksheep import Application, Request, Response, auth, FromJSON
from blacksheep.server.controllers import Controller, delete, get, patch, post
from urllib.parse import quote
from blacksheep.server.dataprotection import get_serializer
from dataclasses import dataclass
import datetime
from guardpost.authentication import Identity

from secrets import token_urlsafe

@dataclass
class Login:
    token: str

class Auth(Controller):
    def __init__(self, app: Application):
        self.app = app

    @classmethod
    def route(cls) -> str:
        return "auth"

    @post("token")
    async def elogin(self, request: Request, data: FromJSON[Login]) -> Response:
        data = data.value
        print(data)

        async with self.app.state["session"].get("https://discord.com/api/users/@me", headers={"Authorization": "Bearer " + data.token}) as  req:
            user = await req.json()

        expiry = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)

        api_token = get_serializer(purpose="token").dumps({"t": user["id"], "e": expiry.isoformat()})

        return self.json({
            "token": api_token,
            "user": user
        })

    @auth()
    @get("protected")
    async def protected(self, user: Identity) -> Response:
        print(user)

        return self.json({"test": "test"})

        
