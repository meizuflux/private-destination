from blacksheep.server import Application
from itsdangerous import BadSignature
from yaml import safe_load
from app import handlers
from app import controllers
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

from dotenv import load_dotenv

load_dotenv()



with open("config.yml") as f:
    config = safe_load(f)

try:
    import uvloop
    uvloop.install()
except ModuleNotFoundError:
    print("Running without `uvloop`")


app = Application(
    show_error_details=bool(config["show_error_details"]),
    debug=bool(config["debug"]),
)

app.use_sessions("<SIGNING_KEY>")

app.state = {
    "config": config,
    "db": {}
}

app.on_start += handlers.before_start
app.after_start += handlers.after_start
app.on_stop += handlers.on_stop

app.serve_files("build", fallback_document="index.html", allow_anonymous=True)


docs = OpenAPIHandler(info=Info(title="Cats API", version="0.0.1"))
docs.include = lambda path, _: path.startswith("/api/")

docs.bind_app(app)

app.use_cors(
    allow_methods="*",
    allow_origins="*",
    allow_headers="* Authorization",
    max_age=300,
)

app.services.add_instance(app)

class AuthHandler(AuthenticationHandler):
    async def authenticate(self, context: Request) -> Optional[Identity]:
        authorization_value = context.get_first_header(b"Authorization")
        print(authorization_value)

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