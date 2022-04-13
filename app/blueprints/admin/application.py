from app.routing import Blueprint
from aiohttp_jinja2 import template
from aiohttp import web
from app.utils.db import (
    select_total_sessions_count,
    select_total_unique_sessions_count,
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
            "session_count": await select_total_sessions_count(conn),
            "unique_session_count": await select_total_unique_sessions_count(conn)
        }

    ctx["cpu"] = {
        "percentage": "%, ".join([str(i) for i in psutil.cpu_percent(percpu=True)]),
        "cores": psutil.cpu_count(),
        "frequency": psutil.cpu_freq().current
    }
    mem = psutil.virtual_memory()
    ctx["memory"] = {
        "total": "{:,.2f} GB".format(mem.total / 1024 / 1024 / 1024),
        "used": "{:,.2f} GB".format(mem.used / 1024 / 1024 / 1024),
        "percent": mem.percent
    }
    drives = []
    for partition in psutil.disk_partitions():
        usage = psutil.disk_usage(partition.mountpoint)
        drives.append({
            "mountpoint": partition.mountpoint,
            "total": f"{usage.total / 1024 / 1024 / 1024:,.2f} GB",
            "used": f"{usage.used / 1024 / 1024 / 1024:,.2f} GB",
            "free": f"{usage.free / 1024 / 1024 / 1024:,.2f} GB",
            "percent": str(usage.percent) + "%"
        })
    counters = psutil.disk_io_counters()
    ctx["disk"] = {
        "drives": drives,
        "count": len(drives),
        "counters": {
            "read_count": f"{counters.read_count:,}",
            "read_bytes": f"{counters.read_bytes / 1024 / 1024 / 1024:,.2f} GB",
            "write_count": f"{counters.write_count:,}",
            "write_bytes": f"{counters.write_bytes / 1024 / 1024 / 1024:,.2f} GB",
        }
    }
    
    p = psutil.Process()
    with p.oneshot():
        ctx["process"] = {
            "memory": "{:,.2f} MB".format(p.memory_full_info().uss / 1024 / 1024),
            "cpu": p.cpu_percent() / ctx["cpu"]["cores"]
        }
        ctx["process"].update(p.as_dict(attrs=["pid", "username", "cwd", "exe", "cmdline"]))

    return ctx