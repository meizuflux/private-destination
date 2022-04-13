from app.routing import Blueprint
from aiohttp_jinja2 import template
from aiohttp import web
from app.utils.db import (
    select_total_sessions_count,
    select_total_short_url_count,
    select_total_users_count
)
import psutil

bp = Blueprint("/admin/application")

@bp.get("")
@template("admin/application.html")
async def index(request: web.Request):
    ctx = {}

    async with request.app["db"].acquire() as conn:
        ctx["service"] = {
            "shortener_count": await select_total_short_url_count(conn),
            "user_count": await select_total_users_count(conn),
            "session_count": await select_total_sessions_count(conn)
        }

    ctx["cpu"] = {
        "percentage": "%, ".join([str(i) for i in psutil.cpu_percent(percpu=True)]),
        "cores": psutil.cpu_count(),
        "frequency": psutil.cpu_freq().current
    }
    mem = psutil.virtual_memory()
    ctx["memory"] = {
        "total": mem.total,
        "used": mem.used,
        "percentage": mem.percent
    }
    drives= [[part.mountpoint, psutil.disk_usage(part.mountpoint)] for part in psutil.disk_partitions()]
    ctx["disk"] = {
        "drives": drives,
        "count": len(drives),
        "counters": psutil.disk_io_counters()
    }
    p = psutil.Process()
    with p.oneshot():
        ctx["process"] = {
            "memory": p.memory_full_info().uss ,
            "cpu": p.cpu_percent() / ctx["cpu"]["cores"]
        }
        ctx["process"].update(p.as_dict(attrs=["pid", "username", "cwd", "exe", "cmdline"]))

    return ctx