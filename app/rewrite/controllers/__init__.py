from typing import List

from app.routing import Controller
from .auth import Auth

def all() -> List[Controller]:
    return (
        Auth,
    )