from typing import List, Union
from uuid import UUID

from asyncpg import Connection, Pool, Record

from app.utils import Scopes, User

ConnOrPool = Union[Connection, Pool]


def form_scopes(scopes: Scopes) -> str:
    return scopes if isinstance(scopes, str) else ", ".join(scopes)


async def select_short_urls(conn: ConnOrPool, *, sortby: str, direction: str, owner: int, offset: int) -> List[Record]:
    # sort and direction weren't working as params to get passed so they have to go directly into the query
    # this is fine as they both are sanitized with the api-spec
    query = f"""
        SELECT key, destination, clicks, creation_date 
        FROM urls 
        WHERE owner = $1
        ORDER BY {sortby} {direction.upper()}
        LIMIT 50
        OFFSET $2
    """
    return await conn.fetch(query, owner, offset)


async def select_short_url_count(conn: ConnOrPool, *, owner: int) -> int:
    return await conn.fetchval("SELECT count(key) FROM urls WHERE owner = $1", owner)


async def insert_short_url(conn: ConnOrPool, *, owner: int, key: str, destination: str):
    return await conn.fetchrow(
        "INSERT INTO urls (owner, key, destination) VALUES ($1, $2, $3)", owner, key, destination
    )


async def update_short_url(conn: ConnOrPool, *, key: str, new_key: str, destination: str, reset_clicks: bool):
    query = "UPDATE urls SET key = $1, destination = $2"
    if reset_clicks:
        query += ", clicks = 0"
    query += " WHERE key = $3"
    return await conn.execute(query, new_key, destination, key)


async def delete_short_url(conn: ConnOrPool, *, key: str):
    return await conn.execute("DELETE FROM urls WHERE key = $1", key)


async def select_short_url_exists(conn: ConnOrPool, *, key: str):
    return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM urls WHERE key = $1)", key)


async def select_short_url_destination(conn: ConnOrPool, *, key: str):
    return await conn.fetchval("SELECT destination FROM urls WHERE key = $1", key)


async def select_short_url(conn: ConnOrPool, *, key: str):
    return await conn.fetchrow("SELECT owner, key, destination, clicks FROM urls WHERE key = $1", key)


async def add_short_url_click(conn: ConnOrPool, *, key: str):
    return await conn.execute("UPDATE urls SET clicks = clicks + 1 WHERE key = $1", key)


async def insert_user(conn: ConnOrPool, *, user: User, hashed_password: str):
    query = """
        INSERT INTO users (username, email, password, api_key)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """
    return await conn.fetchval(query, user["username"], user["email"], hashed_password, user["api_key"])


async def update_user(conn: ConnOrPool, *, user_id: int, username: str, email: str, authorized: bool):
    query = """
        UPDATE users
        SET username = $1, email = $2, authorized = $3
        WHERE id = $4
    """
    return await conn.execute(query, username, email, authorized, user_id)


async def delete_user(conn: ConnOrPool, *, user_id: int):
    return await conn.execute("DELETE FROM users WHERE id = $1", user_id)


async def select_users(conn: ConnOrPool, *, sortby: str, direction: str):
    query = f"""
        SELECT
            id, username, email, joined, authorized
        FROM
            users
        ORDER BY {sortby} {direction.upper()}
        """

    return await conn.fetch(query)


async def select_user(conn: ConnOrPool, *, user_id: int):
    return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)


async def authorize_user(conn: ConnOrPool, *, user_id: int):
    return await conn.execute("UPDATE users SET authorized = true WHERE id = $1", user_id)


async def unauthorize_user(conn: ConnOrPool, *, user_id: int):
    return await conn.execute("UPDATE users SET authorized = false WHERE id = $1", user_id)


async def get_hash_and_id_by_email(conn: ConnOrPool, *, email: str):
    return await conn.fetchrow("SELECT id, password FROM users WHERE email = $1", email)


async def insert_session(conn: ConnOrPool, *, user_id: int, browser: str, os: str):
    return await conn.fetchval(
        "INSERT INTO sessions (token, user_id, browser, os) (SELECT gen_random_uuid(), $1, $2, $3) RETURNING token;",
        user_id,
        browser,
        os,
    )


async def delete_session(conn: ConnOrPool, *, token: UUID):
    return await conn.execute("DELETE FROM sessions WHERE token = $1", token)


async def select_session_exists(conn: ConnOrPool, *, token: UUID):
    return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM sessions WHERE token = $1)", token)


async def select_user_by_session(conn: ConnOrPool, *, token: UUID, scopes: Scopes):
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


async def select_user_by_api_key(conn: ConnOrPool, *, api_key: str, scopes: Scopes):
    return await conn.fetchrow(f"SELECT {form_scopes(scopes)} FROM users WHERE api_key = $1", api_key)
