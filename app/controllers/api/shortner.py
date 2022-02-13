from blacksheep import Response
from blacksheep.server.controllers import ApiController, delete, get, patch, post
from blacksheep.server.responses import text


class Shortner(ApiController):
    @get()
    def get_cats(self) -> Response:
        return text("Hello, World!")