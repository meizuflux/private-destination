import os
import sys

from asyncpg import UniqueViolationError

sys.path.append(os.getcwd())  # weird python module resolution but this works so idk

import asyncio
from getpass import getpass
from sys import argv

from passlib.hash import pbkdf2_sha512
from yaml import safe_load

from app.blueprints.auth import generate_api_key
from app.utils.db import create_pool


async def main():
    del argv[0]  # file invoked
    with open("config.yml") as f:
        loaded = safe_load(f)

    if any([i in argv for i in ("-d", "--dev")]):
        config = loaded["dev"]
    else:
        config = loaded["prod"]

    print("Creating admin user:")

    username = input("Enter username: ")
    email = input("Enter email: ")

    password = getpass("Enter password: ")
    pass2 = getpass("Enter password again: ")

    if password != pass2:
        print("Passwords did not match")
        return

    del pass2

    pw_hash = pbkdf2_sha512.hash(password)

    pool = await create_pool(None, config["postgres_dsn"])
    try:
        user_id = await pool.create_user(
            {"username": username, "email": email, "api_key": await generate_api_key(pool)}, pw_hash
        )
    except UniqueViolationError:
        print("A user with this email already exists")
        await pool.close()
        return
    print("Created user", user_id)
    await pool.execute("UPDATE users SET authorized = True, admin = True WHERE id = $1", user_id)

    print(f"Updated user {user_id} to be authorized with admin permissions")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())