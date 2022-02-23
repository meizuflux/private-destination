from dataclasses import dataclass
from typing import Callable, Dict, Generic, TypeVar, TypedDict

T = TypeVar("T")

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

@dataclass
class User:
    id: str
    name: str
    email: str
    avatar_url: str

    __slots__ = ("id", "name", "avatar_url", "email")

    def __init__(self, info: Dict[str, str]):
        for attr in self.__slots__:
            setattr(self, attr, info.get(attr))

@dataclass
class OAuthProvider(Generic[T]):
    name: str
    urls: OAuthUrls
    
    def parse_data(self, data: Generic[T]) -> User:
        raise NotImplementedError