from typing import Tuple, Type
from app.controllers.dashboard import Dashboard

from app.routing import Controller
from .api.auth import Auth

def all() -> Tuple[Type[Controller]]:
    return (
        Auth,
        Dashboard
    )