run dev with 

```bash
adev runserver --livereload app/__init__.py --app-factory app_factory
```

note for running postgres:

```bash
docker run --name some-postgres --net host -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres
$ psql -h localhost -p 5432 -U postgres
```

uri is `postgres://postgres:mysecretpassword@localhost:5432/postgres`

nginx should serve frontend/dist/assets in production
