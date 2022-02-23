from blacksheep import Application, Request, Response, auth
from blacksheep.server.controllers import ApiController, delete, get, patch, post
from blacksheep.server.responses import text

from typing import Optional
from guardpost.authentication import User

from app.utils.app import CustomApplication


class Shortner(ApiController):
    def __init__(self, app: CustomApplication):
        self.app = app

    @auth()
    @get()
    def get_cats(self, user: Optional[User]) -> Response:
        print(user.claims)

        return text("Hello, World!")

    @get("test")
    async def test(self, request: Request) -> Response:
        request.session["test"] = "testing"

        return self.json({"message": "Hello World!"})

    