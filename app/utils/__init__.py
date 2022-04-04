from enum import Enum
from typing import List, Union

Scopes = Union[List[str], None, str]


class Status(Enum):
    OK = 0
    ERROR = 1
