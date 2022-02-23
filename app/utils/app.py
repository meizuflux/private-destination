from os import environ
from sys import argv
from typing import Dict, Union
from aiohttp import ClientSession
from blacksheep import Application
from yaml import dump, safe_load
from blacksheep.server.openapi.v3 import OpenAPIHandler
from openapidocs.v3 import Info

from app.utils.auth import OAuthProvider


class CustomApplication(Application):
    config: Dict[str, Union[str, int, bool]]
    session: ClientSession
    oauth_providers: Dict[str, OAuthProvider] = {}

    def __init__(self):
        self.IS_DEV = "--reload" in argv

        with open("config.yml") as f:
            loaded = safe_load(f)

            if self.IS_DEV is True:
                config = loaded["dev"]
            else:
                config = loaded["prod"]

        
        for i, secret in enumerate(config["secrets"], start=1):
            environ[f"APP_SECRET_{i}"] = secret

        self.config = config

        super().__init__(
            show_error_details=bool(config["show_error_details"]),
            debug=bool(config["debug"]),
        )

        self.use_sessions(config["signing_key"])

        self.serve_files("frontend/dist", fallback_document="index.html", allow_anonymous=True)

        self.services.add_instance(self)

        docs = OpenAPIHandler(info=Info(title="Cats API", version="0.0.1"))
        docs.include = lambda path, _: path.startswith("/api/")
        docs.bind_app(self)

        self.on_start += on_start
        self.after_start += after_start
        self.on_stop += on_stop

    def add_oauth_provider(self, name: str, provider: OAuthProvider) -> None:
        self.oauth_providers[name] = provider

async def on_start(app: CustomApplication) -> None:
    print("Before start")

    app.session = ClientSession()

async def after_start(app: CustomApplication) -> None:
    final = {k.decode('utf8'): [r.pattern.decode('utf8') for r in v] for (k, v) in dict(app.router.routes).items()}

    print(dump(final))
    print("OAuth2 Providers: ", ", ".join(app.oauth_providers))

async def on_stop(app: CustomApplication) -> None:
    print("On stop")

