from blacksheep import Router
from blacksheep.server import Application
from yaml import safe_load
from app import handlers
from app import controllers
controllers # make it shut up about it being used

from blacksheep.server.openapi.v3 import OpenAPIHandler
from openapidocs.v3 import Info
from app.fallback import fallback


with open("config.yml") as f:
    config = safe_load(f)

try:
    import uvloop
    uvloop.install()
except ModuleNotFoundError:
    print("Running without `uvloop`")

router = Router()
routes = [

]

app = Application(
    show_error_details=bool(config["show_error_details"]),
    debug=bool(config["debug"]),
    router=router
)

app.on_start += handlers.before_start
app.after_start += handlers.after_start
app.on_stop += handlers.on_stop

app.serve_files("build", fallback_document="index.html", allow_anonymous=True)


docs = OpenAPIHandler(info=Info(title="Cats API", version="0.0.1"))
docs.include = lambda path, _: path.startswith("/api/")

docs.bind_app(app)
