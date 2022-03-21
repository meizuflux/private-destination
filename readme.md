```bash
$ psql -h localhost -p 5432 -U postgres
```

uri is `postgres://postgres:mysecretpassword@localhost:5432/postgres`

nginx should serve static in production

# setting up admin user
first set everything up

then go login with your preferred account (github or discord)

next run this sql command however you prefer

```sql
UPDATE users SET authorized = true, admin = True WHERE username = 'your username';
```
you can do it by user_id too or however you please but your user row has to have authorized and admin both be true

# http codes
`401` is for when the user is not logged in

`403` is for when the user is logged in but not allowed to view the resource

`499` is for when the user's account is pending authorization. this technically would fall under `403` but I wanted an easier way to change the error page