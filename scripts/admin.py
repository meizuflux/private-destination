import argparse
import os
import sys

from asyncpg import UniqueViolationError, create_pool

sys.path.append(os.getcwd())  # weird python module resolution but this works so idk

import asyncio
from getpass import getpass

from passlib.hash import pbkdf2_sha512
from yaml import safe_load

from app.utils.auth import generate_api_key
from app.utils.db import insert_user


async def main():
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("-p", "--prod", "--production", action="store_true", dest="production")

    args = parser.parse_args()

    with open("config.yml", encoding="utf-8") as file:
        loaded = safe_load(file)

    if args.production:
        config = loaded["prod"]
    else:
        config = loaded["dev"]

    print("Creating admin user:")

    email = input("Enter email: ")

    password = getpass("Enter password: ")
    password_confirmation = getpass("Enter password again: ")

    if password != password_confirmation:
        print("Passwords did not match")
        return

    del password_confirmation

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
