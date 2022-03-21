run-db:
    docker run --name db --net host -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres

start-db:
    docker start db

dev:
    adev runserver --livereload server.py --app-factory app_factory

venv:
    python -m venv venv

build:
    node build.mjs

watch:
    yarn run chokidar "static/**/*.*" "templates/*.html" -c "node build.mjs" --initial

dbuild:
    docker build -t mzf_one .

drun:
    docker run -dp 8000:8000 -t --name mzf_one mzf_one

