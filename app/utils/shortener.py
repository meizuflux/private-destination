import string
from secrets import choice

from app.utils.db import ConnOrPool, select_short_url_exists

ALPHANUMERIC_CHARS = string.ascii_letters + string.digits


async def generate_url_alias(conn: ConnOrPool):
    while True:
        alias = "".join(choice(ALPHANUMERIC_CHARS) for _ in range(7))
        if await select_short_url_exists(conn, alias=alias) is False:
            break
    return alias
