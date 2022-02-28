from typing import Tuple, Type

from app.routing import Controller
from .auth import Auth

def all() -> Tuple[Type[Controller]]:
    return (
        Auth,
    )