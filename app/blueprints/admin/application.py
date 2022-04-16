import os
import subprocess
from importlib.metadata import version
from pathlib import Path

import psutil
from aiohttp import web
from aiohttp_jinja2 import template

from app.routing import Blueprint
from app.utils.db import (
    select_total_sessions_count,
    select_total_short_url_count,
    select_total_unique_sessions_count,
    select_total_users_count,
)

files = lines = characters = classes = functions = coroutines = comments = 0
for f in Path("./").rglob("*.*"):
    if str(f).startswith("venv") or str(f).startswith(".git") or str(f).startswith("node_modules") or str(f).startswith("dist") or str(f).endswith(".pyc"):
        continue
    files += 1
    with f.open(encoding="utf-8") as of:
        _lines = of.readlines()
        lines += len(_lines)
        for l in _lines:
            l = l.strip()
            characters += len(l)
            if f.suffix == ".py":
                if l.startswith("class"):
                    classes += 1
                if l.startswith("def"):
                    functions += 1
                if l.startswith("async def"):
                    functions += 1
                    coroutines += 1
                if "#" in l:
                    comments += 1
code_stats = {
    "files": f"{files:,}",
    "lines": f"{lines:,}",
    "characters": f"{characters:,}",
    "classes": f"{classes:,}",
    "functions": f"{functions:,}",
    "coroutines": f"{coroutines:,}",
    "comments": f"{comments:,}",
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

bp = Blueprint("/admin/application")


@bp.get("")
@template("admin/application.html")
async def index(request: web.Request):
    ctx = {
        "packages": packages,
        "code_stats": code_stats,
        "git": git_stats,
    }

    async with request.app["db"].acquire() as conn:
        ctx["service"] = {
            "shortener_count": await select_total_short_url_count(conn),
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
        "total": "{:,.2f} GB".format(mem.total / 1024 / 1024 / 1024),
        "used": "{:,.2f} GB".format(mem.used / 1024 / 1024 / 1024),
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

    p = psutil.Process()
    with p.oneshot():
        ctx["process"] = {
            "memory": "{:,.2f} MB".format(p.memory_full_info().uss / 1024 / 1024),
        }
        ctx["process"].update(p.as_dict(attrs=["pid", "username", "cwd", "exe", "cmdline"]))

    return ctx
