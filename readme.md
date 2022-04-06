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
email with `sendinblue`
- password reset
- maybe some progressive enhancement like `hotwire` `htmx` or `hibiki`
- bulma dark theme
- welcome email
- image cdn
- maybe make the site invite only??
- something similar to mystbin/pastebin
- todo list
- log ip with session
- add domain to left of shortner create thingy
- add a few more limits on shortener alias
- email verification