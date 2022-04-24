from aiohttp.web import run_app

from app import app_factory

if __name__ == "__main__":
    run_app(app_factory(), port=8000)
