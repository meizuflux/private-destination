import os
import subprocess
from importlib.metadata import version
from pathlib import Path
from typing import Any

import psutil
from aiohttp import web

from app.routing import Blueprint
from app.templating import render_template
from app.utils.db import (
    get_db,
    select_total_sessions_count,
    select_total_short_urls_count,
    select_total_unique_sessions_count,
    select_total_users_count,
)

FILES = LINES = CHARACTERS = CLASSES = FUNCTIONS = COROUTINES = COMMENTS = 0
for f in Path("./").rglob("*.*"):
    # no idea how do do this with glob so I'm just gonna do this
    # docs: https://docs.python.org/3/library/fnmatch.html#fnmatch.fnmatch
    ignored_folders = ("venv", "node_modules", "dist", ".git", ".vscode", ".mypy_cache")
    ignored_extensions = (".pyc",)
    if any(str(f).startswith(folder) for folder in ignored_folders):
        continue
    if any(str(f).endswith(ext) for ext in ignored_extensions):
        continue

    FILES += 1
    with f.open(encoding="utf-8") as of:
        _lines = of.readlines()
        LINES += len(_lines)
        for l in _lines:
            l = l.strip()
            CHARACTERS += len(l)
            if f.suffix == ".py":
                if l.startswith("class"):
                    CLASSES += 1
                if l.startswith("def"):
                    FUNCTIONS += 1
                if l.startswith("async def"):
                    FUNCTIONS += 1
                    COROUTINES += 1
                if "#" in l:
                    COMMENTS += 1
code_stats = {
    "files": f"{FILES:,}",
    "lines": f"{LINES:,}",
    "characters": f"{CHARACTERS:,}",
    "classes": f"{CLASSES:,}",
    "functions": f"{FUNCTIONS:,}",
    "coroutines": f"{COROUTINES:,}",
    "comments": f"{COMMENTS:,}",
}

_pkgs = ["aiohttp", "gunicorn", "asyncpg", "marshmallow", "passlib", "psutil", "jinja2"]

if os.name != "nt":
    _pkgs.append("uvloop")

packages = {pkg: version(pkg) for pkg in _pkgs}

revision = subprocess.getoutput("git rev-parse HEAD")
short_revision = revision[:7]
remote = subprocess.getoutput("git config --get remote.origin.url")
git_stats = {
    "revision": revision[:7],
    "branch": subprocess.getoutput("git rev-parse --abbrev-ref HEAD"),
    "remote": remote,
    "commit_count": subprocess.getoutput("git rev-list --count HEAD"),
    "commit_message": subprocess.getoutput("git log -1 --pretty=%B").strip(),
    "commit_url": f"https://github.com/{'/'.join(remote.split('/')[-2:]).removesuffix('.git')}/commit/{revision}",
}

bp = Blueprint("/admin/application", name="application")


@bp.get("", name="index")
async def index(request: web.Request) -> web.Response:
    ctx: dict[str, Any] = {
        "packages": packages,
        "code_stats": code_stats,
        "git": git_stats,
    }

    async with get_db(request).acquire() as conn:
        ctx["service"] = {
            "shortener_count": await select_total_short_urls_count(conn),
            "user_count": await select_total_users_count(conn),
            "session_count": await select_total_sessions_count(conn),
            "unique_session_count": await select_total_unique_sessions_count(conn),
        }

    ctx["cpu"] = {
        "percentage": "%, ".join([str(i) for i in psutil.cpu_percent(percpu=True)]),
        "cores": psutil.cpu_count(),
        "frequency": psutil.cpu_freq().current,
    }
    mem = psutil.virtual_memory()
    ctx["memory"] = {
        "total": f"{mem.total / 1024 / 1024 / 1024:,.2f} GB",
        "used": f"{mem.used / 1024 / 1024 / 1024:,.2f} GB",
        "percent": mem.percent,
    }
    drives = []
    for partition in psutil.disk_partitions():
        usage = psutil.disk_usage(partition.mountpoint)
        drives.append(
            {
                "mountpoint": partition.mountpoint,
                "total": f"{usage.total / 1024 / 1024 / 1024:,.2f} GB",
                "used": f"{usage.used / 1024 / 1024 / 1024:,.2f} GB",
                "free": f"{usage.free / 1024 / 1024 / 1024:,.2f} GB",
                "percent": f"{str(usage.percent)}%",
            }
        )
    counters = psutil.disk_io_counters()
    ctx["disk"] = {
        "drives": drives,
        "count": len(drives),
        "counters": {
            "read_count": f"{counters.read_count:,}",
            "read_bytes": f"{counters.read_bytes / 1024 / 1024 / 1024:,.2f} GB",
            "write_count": f"{counters.write_count:,}",
            "write_bytes": f"{counters.write_bytes / 1024 / 1024 / 1024:,.2f} GB",
        },
    }

    proc = psutil.Process()
    with proc.oneshot():
        ctx["process"] = {
            "memory": f"{proc.memory_full_info().uss / 1024 / 1024:,.2f} MB",
        }
        ctx["process"].update(proc.as_dict(attrs=["pid", "username", "cwd", "exe", "cmdline"]))

    return await render_template("admin/application", request, ctx)
