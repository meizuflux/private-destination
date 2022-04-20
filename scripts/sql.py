import asyncio
from asyncpg import connect

import argparse
import yaml

async def main():
    parser = argparse.ArgumentParser(description="Execute SQL queries against the database")

    parser.add_argument("-c", "--command", dest="command", help="The SQL command to execute")
    parser.add_argument("-f", "--file", dest="file", help="The file containing the SQL command to execute")
    parser.add_argument("-p", "--production", dest="production", action="store_true", help="Use production config", default=False)

    args = parser.parse_args()

    with open("config.yml") as f:
        loaded = yaml.safe_load(f)
        config = loaded["prod"] if args.production is True else loaded["dev"]

    conn = await connect(config["postgres_dsn"])

    if args.command and args.file:
        print("You can only specify a command or a file, not both")
        exit(1)

    if not args.command and not args.file:
        print("You must specify either a command or a file")
        exit(1)

    if args.command:
        print(f"Executing command: {args.command}")
        result = await conn.fetch(args.command)
        for row in result:
            print(row)
    
    if args.file:
        print(f"Executing file: {args.file}")
        with open(args.file) as f:
            content = f.read()
        if len(content.split(";")) > 1: # multiple commands (can't use with conn.fetch)
            print("Using execute instead of fetch")
            result = await conn.execute(content)
        else:
            result = await conn.fetch(content)
        if isinstance(result, list):
            for row in result:
                print(row)
        else:
            print(result)

if __name__ == "__main__":
    asyncio.run(main())