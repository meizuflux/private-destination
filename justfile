run-db:
    docker run --name db --net host -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres

start-db:
    docker start db

dev:
    adev runserver --livereload server.py --app-factory app_factory

venv:
    python -m venv venv

build:
    node scripts/build.mjs && node scripts/code-editor.mjs

watch:
    yarn run chokidar "static/**/*.*" "templates/*.html" -c "node build.mjs" --initial

