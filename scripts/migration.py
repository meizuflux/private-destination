import asyncio
from datetime import datetime
from sys import argv
import asyncpg
from yaml import safe_load

async def main():
    with open("config.yml", "r") as f:
        config = safe_load(f)
    if "--prod" in argv:
        db_dsn = config["prod"]["postgres_dsn"]
    else:
        db_dsn = config["dev"]["postgres_dsn"]

    print("Enter database migration. Press Ctrl-D or Ctrl-Z ( windows ) to save it.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        lines.append(line)

    migration = "\n".join(lines)

    conn = await asyncpg.connect(dsn=db_dsn)

    await conn.execute(migration)

    filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".sql"
    with open(filename, "w") as f:
        f.write(migration)
    print(f"Migration saved to {filename}")

if __name__ == "__main__":
    asyncio.run(main())

