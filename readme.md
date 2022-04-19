```bash
$ psql -h localhost -p 5432 -U postgres
```
### run migration
```bash
$ psql [options] < migrations/[time].sql
```

uri is `postgres://postgres:mysecretpassword@localhost:5432/postgres`

nginx should serve static in production

# setting up admin user
first create tables
```bash
$ psql [options] < schema.sql
```

then run `scripts/admin.py [--dev]` and follow the prompt. this will create an admin user with the credentials you provide

# http codes
`401` is for when the user is not logged in

`403` is for when the user is logged in but not allowed to view the resource

`499` is for when the user's account is pending authorization. this technically would fall under `403` but I wanted an easier way to change the error page

# todo list
email with `sendinblue`
- password reset
- some progressive enhancement like `hotwire` `htmx` or `hibiki`
- bulma dark theme
- welcome email
- image cdn
- maybe make the site invite only??
- todo list
- email verification
- seperate admin dashboard to manage *everything*, not just users
- panel on admin dashboard to view process usage
- allow use of user password to unlock secure note content
- migrate to argon2_cffi for password hashing

# invite only pondering
```sql
create table if not exists invites (
    user_id bigint references users(id) on delete cascade,
    code text not null primary key,
    used bigint references users (id) on delete cascate default null, -- the user who signed up
    required_email text default null,
)
```
then can track count, and easily generate/delete without needing to change users

might want to add `invite_code` field to user obj to track