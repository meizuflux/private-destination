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

then run `scripts/admin.py [--production]` and follow the prompt. this will create an admin user with the credentials you provide

# todo list
email with `sendinblue`
- password reset
- todo list
- seperate admin dashboard to manage *everything*, not just users
- allow use of user password to unlock secure note content
- migrate to nacl.pwhash.argon2id for password hashing
- make api key encrypted with user's password - so its not in plaintext
- pull out common jinja2 html components into a macro or component file
- migrate users id to use identity
- add editing and deleting of notes
- add a decorator to allow routes to return 2 different types of responses (json and html) based on content type to allow it to act more like an api and reenable sharex compatibility
- polls service
- remove need for email (make it optional) and allow password reset via a secure secret that is shown once
- make account ids similar to mullvad instead of email
- gradually migrate to a REST api (use some minimal js on the frontend to send requests and whatnot)
