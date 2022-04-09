run-db:
    docker run --name db --net host -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres

start-db:
    docker start db

dev:
    adev runserver server.py --app-factory app_factory --host 0.0.0.0

format:
    isort . && black .

build:
    node scripts/build.mjs && node scripts/code-editor.mjs

watch:
    yarn run chokidar "static/**/*.*" "views/*.html" -c "node scripts/build.mjs" --initial

