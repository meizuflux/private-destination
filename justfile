run-db:
    docker run --name db --net host -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres

start-db:
    docker start db

dev:
    adev runserver server.py --app-factory app_factory --host 0.0.0.0

format:
    isort . && black .

build:
    node scripts/build.mjs

watch:
    yarn run chokidar "static/**/*.*" "templates/*.html.jinja" -c "node scripts/build.mjs" --initial

install:
    pip install -r requirements.txt && pip install -r requirements-dev.txt

pyenv:
    pyenv install 3.10.2 && pyenv global 3.10.2
