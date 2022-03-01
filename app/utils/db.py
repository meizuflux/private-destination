from uuid import UUID, uuid4

from app.utils.auth import User
from asyncpg import Connection, Pool, Record


class Database(Pool):
    __data = {
        "sessions": {},
        "users": {}
    }

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

    async def create_user(self, user: User, provider: str):
        query = """
            INSERT INTO users (user_id, username, email, avatar_url, oauth_provider) VALUES ($1, $2, $3, $4, $5) 
            ON CONFLICT (user_id) DO UPDATE SET
            username = $2, email = $3, avatar_url = $4, oauth_provider = $5
            WHERE users.user_id = $1;
        """
        await self.execute(query, user["id"], user["username"], user["email"], user["avatar_url"], provider)

    async def fetch_user(self, uuid: UUID):
        return await self.fetchrow("SELECT * FROM users WHERE user_id = (SELECT user_id FROM sessions WHERE token = $1);", uuid)

    async def create_session(self, user_id: int, *, browser: str, os: str):
        token = await self.fetchval("INSERT INTO sessions (token, user_id, browser, os) (SELECT gen_random_uuid(), $1, $2, $3) RETURNING token;", user_id, browser, os)
        return token

    async def delete_session(self, token: UUID):
        await self.execute("DELETE FROM sessions WHERE token = $1", token)

    async def check_session(self, uuid: UUID):
        return await self.fetchval("SELECT EXISTS(SELECT 1 FROM sessions WHERE id = $1", uuid)

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

