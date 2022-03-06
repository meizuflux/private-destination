postgres:
    docker run --name some-postgres --net host -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres

dev:
    adev runserver --livereload server.py --app-factory app_factory

linuxdev:
    ./venv/bin/adev runserver --livereload app/__init__.py --app-factory app_factory

venv:
    python -m venv venv

build:
    yarn run rimraf dist && node build.mjs

watch:
    yarn run chokidar "static/*.*" "templates/*.html" -c "node build.mjs" --initial

