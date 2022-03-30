```bash
$ psql -h localhost -p 5432 -U postgres
```

uri is `postgres://postgres:mysecretpassword@localhost:5432/postgres`

nginx should serve static in production

# setting up admin user
first run it once to create tables

then run `scripts/admin.py` and follow the prompt. this will create an admin user with the credentials you provide

# http codes
`401` is for when the user is not logged in

`403` is for when the user is logged in but not allowed to view the resource

`499` is for when the user's account is pending authorization. this technically would fall under `403` but I wanted an easier way to change the error page

# todo list
rewrite app to use raw html forms instead of js because I hate JS with a passion

maybe password reset(?)

maybe a bulma dark theme since light theme burns my eyes

*maybe* use `hotwire` or `htmx`