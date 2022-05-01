from typing import List, Union, cast
from uuid import UUID

from asyncpg import Connection, Pool, Record
from aiohttp import web

from app.utils import QueryScopes

ConnOrPool = Union[Connection, Pool]


def form_scopes(scopes: QueryScopes) -> str:
    return scopes if isinstance(scopes, str) else ", ".join(scopes)

def get_db(request_or_app: web.Request | web.Application) -> Pool:
    if isinstance(request_or_app, web.Request):
        app = request_or_app.app
    return cast(Pool, app["db"])


async def select_notes(conn: ConnOrPool, *, sortby: str, direction: str, owner: int, offset: int) -> List[Record]:
    # sort and direction weren't working as params to get passed so they have to go directly into the query
    # this is fine as they both are sanitized with the api-spec
    query = f"""
        SELECT encode(convert_to(cast(id as text), 'UTF8'), 'base64') AS id, owner, name, content, has_password, share_email, private, clicks, creation_date
        FROM notes
        WHERE owner = $1
        ORDER BY {sortby} {direction.upper()}
        LIMIT 50
        OFFSET $2
    """
    return await conn.fetch(query, owner, offset)


async def select_notes_count(conn: ConnOrPool, *, owner: int) -> int:
    return await conn.fetchval("SELECT count(id) FROM notes WHERE owner = $1", owner)


async def select_total_notes_count(conn: ConnOrPool) -> int:
    return await conn.fetchval("SELECT count(id) FROM notes")


async def select_short_urls(conn: ConnOrPool, *, sortby: str, direction: str, owner: int, offset: int) -> List[Record]:
    # sort and direction weren't working as params to get passed so they have to go directly into the query
    # this is fine as they both are sanitized with the api-spec
    query = f"""
        SELECT alias, destination, clicks, creation_date 
        FROM urls 
        WHERE owner = $1
        ORDER BY {sortby} {direction.upper()}
        LIMIT 50
        OFFSET $2
    """
    return await conn.fetch(query, owner, offset)


async def select_short_urls_count(conn: ConnOrPool, *, owner: int) -> int:
    return await conn.fetchval("SELECT count(alias) FROM urls WHERE owner = $1", owner)


async def select_total_short_urls_count(conn: ConnOrPool):
    return await conn.fetchval("SELECT count(alias) FROM urls")


async def insert_short_url(conn: ConnOrPool, *, owner: int, alias: str, destination: str):
    return await conn.fetchrow(
        "INSERT INTO urls (owner, alias, destination) VALUES ($1, $2, $3)", owner, alias, destination
    )


async def update_short_url(conn: ConnOrPool, *, alias: str, new_alias: str, destination: str, reset_clicks: bool):
    query = "UPDATE urls SET alias = $1, destination = $2"
    if reset_clicks is True:
        query += ", clicks = 0"
    query += " WHERE alias = $3"
    return await conn.execute(query, new_alias, destination, alias)


async def delete_short_url(conn: ConnOrPool, *, alias: str):
    return await conn.execute("DELETE FROM urls WHERE alias = $1", alias)


async def select_short_url_exists(conn: ConnOrPool, *, alias: str):
    return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM urls WHERE alias = $1)", alias)


async def select_short_url_destination(conn: ConnOrPool, *, alias: str):
    return await conn.fetchval("SELECT destination FROM urls WHERE alias = $1", alias)


async def select_short_url(conn: ConnOrPool, *, alias: str):
    return await conn.fetchrow("SELECT owner, alias, destination, clicks FROM urls WHERE alias = $1", alias)


async def add_short_url_click(conn: ConnOrPool, *, alias: str):
    return await conn.execute("UPDATE urls SET clicks = clicks + 1 WHERE alias = $1", alias)


async def insert_user(conn: ConnOrPool, *, email: str, api_key: str, hashed_password: str):
    query = """
        INSERT INTO users (email, password, api_key)
        VALUES ($1, $2, $3)
        RETURNING id
    """
    return await conn.fetchval(query, email, hashed_password, api_key)


async def update_user(conn: ConnOrPool, *, user_id: int, email: str, session_duration: int):
    query = """
        UPDATE users
        SET email = $2, session_duration = $3
        WHERE id = $1
    """
    return await conn.execute(query, user_id, email, session_duration)


async def delete_user(conn: ConnOrPool, *, user_id: int):
    return await conn.execute("DELETE FROM users WHERE id = $1", user_id)


async def select_users(conn: ConnOrPool, *, sortby: str, direction: str):
    query = f"""
        SELECT
            id, email, joined
        FROM
            users
        ORDER BY {sortby} {direction.upper()}
        """

    return await conn.fetch(query)


async def select_total_users_count(conn: ConnOrPool):
    return await conn.fetchval("SELECT count(id) FROM users")


async def select_user(conn: ConnOrPool, *, user_id: int):
    return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)


async def get_hash_and_id_by_email(conn: ConnOrPool, *, email: str):
    return await conn.fetchrow("SELECT id, password FROM users WHERE email = $1", email)


async def insert_session(conn: ConnOrPool, *, user_id: int, browser: str, os: str):
    query = """
        INSERT INTO sessions (token, user_id, browser, os) 
        (SELECT gen_random_uuid(), $1, $2, $3) 
        RETURNING token;
    """  # don't add VALUES before the values, it breaks it
    # I have no idea why but this works
    return await conn.fetchval(query, user_id, browser, os)


async def delete_session(conn: ConnOrPool, *, token: UUID):
    return await conn.execute("DELETE FROM sessions WHERE token = $1", token)


async def select_session_exists(conn: ConnOrPool, *, token: UUID):
    return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM sessions WHERE token = $1)", token)


async def select_total_sessions_count(conn: ConnOrPool):
    return await conn.fetchval("SELECT count(token) FROM sessions")


async def select_total_unique_sessions_count(conn: ConnOrPool):
    return await conn.fetchval("SELECT count(DISTINCT user_id) FROM sessions")


async def select_user_by_session(conn: ConnOrPool, *, token: UUID, scopes: QueryScopes):
    return await conn.fetchrow(
        f"SELECT {form_scopes(scopes)} FROM users WHERE id = (SELECT user_id FROM sessions WHERE token = $1);",
        token,
    )


async def select_sessions(conn: ConnOrPool, *, user_id: int):
    return await conn.fetch(
        "SELECT token, created, browser, os FROM sessions WHERE user_id = $1 ORDER BY created DESC", user_id
    )


async def select_api_key_exists(conn: ConnOrPool, *, api_key: str):
    return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE api_key = $1);", api_key)


async def update_api_key(conn: ConnOrPool, *, user_id: int, api_key: str):
    return await conn.execute("UPDATE users SET api_key = $2 WHERE id = $1", user_id, api_key)


async def select_user_by_api_key(conn: ConnOrPool, *, api_key: str, scopes: QueryScopes):
    return await conn.fetchrow(f"SELECT {form_scopes(scopes)} FROM users WHERE api_key = $1", api_key)
