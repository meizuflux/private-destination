from typing import Tuple, Type
from app.controllers.api.shortner import Shortner
from app.controllers.dashboard import Dashboard

from app.routing import Controller
from .api.auth import Auth

def all():
    return (
        Auth,
        Dashboard,
        Shortner
    )