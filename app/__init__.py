from uuid import UUID
from app import controllers
from app.utils.app import CustomApplication
from app.utils.auth import Credentials
from app.utils.auth.providers import DiscordProvider, GithubProvider
controllers # make it shut up about it being used

from guardpost.common import AuthenticatedRequirement
from blacksheep.server.authorization import Policy
from typing import Optional

from blacksheep import Request
from guardpost.asynchronous.authentication import AuthenticationHandler, Identity

try:
    import uvloop
    uvloop.install()
except ModuleNotFoundError:
    print("Running without `uvloop`")

app = CustomApplication()

app.add_oauth_provider("github", GithubProvider(credentials=Credentials(app.config["github"]["client_id"], app.config["github"]["client_secret"])))
app.add_oauth_provider("discord", DiscordProvider(credentials=Credentials(app.config["discord"]["client_id"], app.config["discord"]["client_secret"])))


class AuthHandler(AuthenticationHandler):
    async def authenticate(self, context: Request) -> Optional[Identity]:
        uuid = context.get_cookie("id")
        if uuid is not None:
            user = await app.db.fetch_user(UUID(uuid))
            context.identity = Identity(user, "oauth_" + user["provider"])
            return context.identity
        return context.identity


app.use_authentication().add(AuthHandler())

# enable authorization, and add a policy that requires an authenticated user
app.use_authorization().add(Policy("authenticated", AuthenticatedRequirement()))