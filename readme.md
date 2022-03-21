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