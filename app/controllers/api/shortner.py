from blacksheep import Application, Response, auth
from blacksheep.server.controllers import ApiController, delete, get, patch, post
from blacksheep.server.responses import text

from typing import Optional
from guardpost.authentication import User


class Shortner(ApiController):
    def __init__(self, app: Application):
        self.app = app

    @auth()
    @get()
    def get_cats(self, user: Optional[User]) -> Response:
        print(user.claims)

        return text("Hello, World!")

    