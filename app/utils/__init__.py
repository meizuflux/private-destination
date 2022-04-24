from enum import Enum
from typing import Iterable, List, Union

Scopes = list[str] | None | str
QueryScopes = list[str] | str


class Status(Enum):
    OK = 0
    ERROR = 1
