from math import ceil
from typing import List, Union
from uuid import UUID

from asyncpg import Connection, Pool, Record

from app.utils.auth import Scopes, User


def form_scopes(scopes: Scopes) -> str:
    if isinstance(scopes, str):
        return scopes
    return ", ".join(scopes)

ConnOrPool = Union[Connection, Pool]

async def select_short_urls(
    conn: ConnOrPool,
    *,
    sortby: str,
    direction: str,
    owner: int,
    offset: int
) -> List[Record]:
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

async def select_short_url_count(conn: ConnOrPool, owner: int) -> int
    return await conn.fetchval("SELECT count(key) FROM urls WHERE owner = $1", owner)


class Database(Pool):
    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

    async def create_user(self, user: User, hashed_password: str):
        query = """
            INSERT INTO users (username, email, password, api_key)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """
        return await self.fetchval(query, user["username"], user["email"], hashed_password, user["api_key"])

    async def delete_user(self, user_id: int):
        return await self.execute("DELETE FROM users WHERE id = $1", user_id)

    async def get_users(self, sortby: str, direction: str):
        query = f"""
            SELECT
                id, username, email, joined, authorized
            FROM
                users
            ORDER BY {sortby} {direction.upper()}
            """

        return await self.fetch(query)

    async def authorize_user(self, user_id: int):
        return await self.execute("UPDATE users SET authorized = true WHERE id = $1", user_id)

    async def unauthorize_user(self, user_id: int):
        return await self.execute("UPDATE users SET authorized = false WHERE id = $1", user_id)

    async def get_hash_and_id(self, email: str):
        return await self.fetchrow("SELECT id, password FROM users WHERE email = $1", email)

    async def create_session(self, user_id: int, *, browser: str, os: str):
        return await self.fetchval(
            "INSERT INTO sessions (token, user_id, browser, os) (SELECT gen_random_uuid(), $1, $2, $3) RETURNING token;",
            user_id,
            browser,
            os,
        )

    async def delete_session(self, token: UUID):
        return await self.execute("DELETE FROM sessions WHERE token = $1", token)

    async def validate_session(self, uuid: UUID):
        return await self.fetchval("SELECT EXISTS(SELECT 1 FROM sessions WHERE token = $1)", uuid)

    async def fetch_user_by_session(self, uuid: UUID, scopes: Scopes):
        return await self.fetchrow(
            f"SELECT {form_scopes(scopes)} FROM users WHERE id = (SELECT user_id FROM sessions WHERE token = $1);",
            uuid,
        )

    async def fetch_sessions(self, user_id: int):
        return await self.fetch("SELECT token, created, browser, os FROM sessions WHERE user_id = $1 ORDER BY created", user_id)

    async def validate_api_key(self, api_key: str):
        return await self.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE api_key = $1);", api_key)

    async def update_api_key(self, user_id: int, api_key: str):
        return await self.execute("UPDATE users SET api_key = $2 WHERE id = $1", user_id, api_key)

    async def fetch_user_by_api_key(self, api_key: str, scopes: Scopes):
        return await self.fetchrow(f"SELECT {form_scopes(scopes)} FROM users WHERE api_key = $1", api_key)

    async def create_short_url(self, owner: int, key: str, destination: str):
        return await self.fetchrow(
            "INSERT INTO urls (owner, key, destination) VALUES ($1, $2, $3)", owner, key, destination
        )

    async def delete_short_url(self, key: str):
        return await self.execute("DELETE FROM urls WHERE key = $1", key)

    async def check_short_url_exists(self, key: str):
        return await self.fetchval("SELECT EXISTS(SELECT 1 FROM urls WHERE key = $1)", key)

    async def get_short_url_destination(self, key: str):
        return await self.fetchval("SELECT destination FROM urls WHERE key = $1", key)

    async def add_short_url_click(self, key: str):
        return await self.execute("UPDATE urls SET clicks = clicks + 1 WHERE key = $1", key)

    async def get_short_url_count(self, owner: int):
        return await self.fetchval("SELECT count(key) FROM urls WHERE owner = $1", owner)

    async def get_short_urls(self, *, sortby: str, direction: str, owner: int, offset: int):
        # sort and direction weren't working as args to get passed so they have to go directly into the query
        # this is fine as they both are sanitized with the api-spec
        query = f"""
            SELECT key, destination, clicks, creation_date 
            FROM urls 
            WHERE owner = $1
            ORDER BY {sortby} {direction.upper()}
            LIMIT 50
            OFFSET $2
            """
        return await self.fetch(query, owner, offset)

    async def get_short_url_max_pages(self, owner: int) -> int:
        urls = await self.fetchval("SELECT count(key) FROM urls WHERE owner = $1", owner)
        return ceil(urls / 50)


def create_pool(
    app,
    dsn=None,
    *,
    min_size=10,
    max_size=10,
    max_queries=50000,
    max_inactive_connection_lifetime=300.0,
    setup=None,
    init=None,
    loop=None,
    connection_class=Connection,
    record_class=Record,
    **connect_kwargs,
) -> Database:
    return Database(
        app,
        dsn,
        connection_class=connection_class,
        record_class=record_class,
        min_size=min_size,
        max_size=max_size,
        max_queries=max_queries,
        loop=loop,
        setup=setup,
        init=init,
        max_inactive_connection_lifetime=max_inactive_connection_lifetime,
        **connect_kwargs,
    )
