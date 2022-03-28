from dataclasses import dataclass
from typing import Dict, List, TypedDict, Union

Scopes = Union[List[str], None, str]


@dataclass
class AuthorizationUrl:
    url: str
    state: bool
    params: Dict[str, str]


@dataclass
class OAuthUrls:
    authorization: AuthorizationUrl
    token: str
    user: str


class User(TypedDict):
    id: str
    username: str
    email: str
    avatar_url: str


@dataclass
class Credentials:
    client_id: str
    client_secret: str


@dataclass
class OAuthProvider:
    name: str
    urls: OAuthUrls
    credentials: Credentials

    def __init__(self, credentials: Credentials):
        self.credentials = credentials

    @staticmethod
    def parse_data(data) -> User:
        raise NotImplementedError


def requires_auth(
    *,
    admin: bool = False,
    redirect: bool = False,
    scopes: Scopes = None,  # a tuple represents the columns, a false means don't fetch the user, and true means to get all columns (*)
):
    if scopes is not None:
        if isinstance(scopes, str):
            scopes = [scopes]
    else:
        scopes = []
    if not (len(scopes) == 1 and scopes[0] == "*"):
        if admin is True:
            scopes.append("admin")
        scopes.append("authorized")

    def deco(fn):
        setattr(fn, "requires_auth", True)
        setattr(fn, "auth", {"admin": admin, "redirect": redirect, "scopes": scopes})
        return fn

    return deco
