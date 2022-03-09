from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Generic, TypeVar, TypedDict

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

class AuthenticationScheme(Enum):
    SESSION = 1
    API_KEY = 2
    BOTH = 3

def requires_auth(*, 
    admin: bool = False,
    scheme: AuthenticationScheme = AuthenticationScheme.BOTH,
    redirect: bool = False,
    wants_user_info: bool = True
):
    def deco(fn):
        setattr(fn, "requires_auth", True)
        setattr(fn, "auth", {
            "admin": admin,
            "scheme": scheme,
            "redirect": redirect,
            "wants_user_info": wants_user_info
        })
        return fn
    return deco