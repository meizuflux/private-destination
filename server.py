from app import app_factory
from aiohttp.web import run_app

if __name__ == "__main__":
    run_app(app_factory(), port=8000)