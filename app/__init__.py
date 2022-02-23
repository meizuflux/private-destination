from urllib.parse import urlencode
from blacksheep.server import Application
from itsdangerous import BadSignature
from yaml import safe_load
from app import handlers
from app import controllers
from app.utils.app import CustomApplication
controllers # make it shut up about it being used

from datetime import timezone, datetime

from blacksheep.server.openapi.v3 import OpenAPIHandler
from openapidocs.v3 import Info
from guardpost.common import AuthenticatedRequirement
from blacksheep.server.authorization import Policy, auth
from typing import Optional

from blacksheep import Application, Request, json
from guardpost.asynchronous.authentication import AuthenticationHandler, Identity
from guardpost.authentication import User
from blacksheep.server.dataprotection import get_serializer

from os import environ
from sys import argv

try:
    import uvloop
    uvloop.install()
except ModuleNotFoundError:
    print("Running without `uvloop`")

IS_DEV = "--reload" in argv

with open("config.yml") as f:
    loaded = safe_load(f)

    if IS_DEV is True:
        config = loaded["dev"]
    else:
        config = loaded["prod"]

for i, secret in enumerate(config["secrets"], start=1):
    environ[f"APP_SECRET_{i}"] = secret


app = CustomApplication()

app.add_oauth_provider("discord", {
    "name": "Discord",
    "urls": {
        "authorization": {
            "url": "https://discord.com/api/oauth2/authorize",
            "state": True,
            "params": {
                "response_type": "code",
                "client_id": app.config["discord"]["client_id"],
                "scope": "identify email",
                "redirect_uri": app.config["callback_url"],
                "prompt": "consent"
            }
        },
        "token": "https://discord.com/api/oauth2/token",
        "user": "https://discord.com/api/users/@me"
    }
})


class AuthHandler(AuthenticationHandler):
    async def authenticate(self, context: Request) -> Optional[Identity]:
        authorization_value = context.get_first_header(b"Authorization")
        if not authorization_value:
            context.identity = Identity({})
            return None

        if not authorization_value.startswith(b"Bearer "):
            context.identity = Identity({})
            return None

        token = authorization_value[7:].decode()

        try:
            decoded = get_serializer(purpose="token").loads(token)
            print(decoded)
        except BadSignature:
            pass
        else:
            if datetime.fromisoformat(decoded["e"]) < datetime.now(timezone.utc):
                context.identity = Identity({})
                return None

            context.identity = Identity(decoded, "discord")
            return context.identity
        return context.identity


app.use_authentication().add(AuthHandler())

# enable authorization, and add a policy that requires an authenticated user
app.use_authorization().add(Policy("authenticated", AuthenticatedRequirement()))