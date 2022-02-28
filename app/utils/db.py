from uuid import UUID, uuid4

from app.utils.auth import User
from asyncpg import Connection, Pool, Record


class Database(Pool):
    __data = {
        "sessions": {},
        "users": {}
    }

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = bot

    async def create_user(self, user: User, provider: str):
        query = """
            insert into users (id, username, email, avatar_url, provider) values ($1, $2, $3, $4, $5) on conflict (id) do update set 
            username = $2, email = $3, avatar_url = $4, provider = $5
            where users.id = $1;
        """
        await self.execute(query, user["id"], user["username"], user["email"], user["avatar_url"], provider)

    async def fetch_user(self, uuid: UUID):
        return await self.fetchrow("SELECT * FROM users WHERE id = (SELECT user_id FROM sessions WHERE id =$1);", uuid)

    async def create_session(self, user_id: str):
        uuid = await self.fetchval("INSERT INTO sessions (SELECT gen_random_uuid(), $1) RETURNING id;", user_id)
        return uuid

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

