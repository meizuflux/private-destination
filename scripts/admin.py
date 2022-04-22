import os
import sys

from asyncpg import UniqueViolationError, create_pool

sys.path.append(os.getcwd())  # weird python module resolution but this works so idk

import asyncio
from getpass import getpass
from sys import argv

from passlib.hash import pbkdf2_sha512
from yaml import safe_load

from app.utils.auth import generate_api_key
from app.utils.db import insert_user


async def main():
    del argv[0]  # file invoked
    with open("config.yml") as f:
        loaded = safe_load(f)

    if any([i in argv for i in ("-d", "--dev")]):
        config = loaded["dev"]
    else:
        config = loaded["prod"]

    print("Creating admin user:")

    email = input("Enter email: ")

    password = getpass("Enter password: ")
    pass2 = getpass("Enter password again: ")

    if password != pass2:
        print("Passwords did not match")
        return

    del pass2

    pw_hash = pbkdf2_sha512.hash(password)

    pool = await create_pool(config["postgres_dsn"])
    try:
        user_id = await insert_user(
            pool,
            email=email,
            api_key=await generate_api_key(pool),
            hashed_password=pw_hash,
        )
    except UniqueViolationError:
        print("A user with this email already exists")
        await pool.close()
        return
    print("Created user", user_id)
    await pool.execute("UPDATE users SET admin = True WHERE id = $1", user_id)

    print(f"Updated user {user_id} to have admin permissions")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
