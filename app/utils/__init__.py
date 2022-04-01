from datetime import datetime
from typing import List, TypedDict, Union

Scopes = Union[List[str], None, str]


class User(TypedDict):
    id: str
    username: str
    email: str
    api_key: str
    joined: datetime
    authorized: bool
    admin: bool
