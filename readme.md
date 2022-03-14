```bash
$ psql -h localhost -p 5432 -U postgres
```

uri is `postgres://postgres:mysecretpassword@localhost:5432/postgres`

nginx should serve static in production

ok here's the plan:

### auth:
API Key goes in `x-api-key` header OR session goes in a cookie named `_session`

api routes can be accessed with both, but the dashboard and all those services require a session


### url shortner:

object:

```json
{
    "key": "abcd",
    "target": "https://meizuflux.com",
    "creation": "smth in iso format",
    "owner": 12341234,
    "views": 69
}
```

```
POST /api/shortner
data: {
    "key": "abcd" # or none which will generate it on the server
    "target": "https://meizuflux.com" # obvious
}
response: new short url
```

```
GET /api/shortner/list(offset=50)(sortby=creation)
response: list of created short urls (max 50)
```

```
PUT /api/shortner/{key}
overwrites previous short url
```

```
GET /api/shortner/{key}
response: the short url with that key
```

```
DELETE /api/shortner/{key}
response: none
```