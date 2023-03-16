# TradeCore API - captured walkthrough

Real transcript against a freshly migrated SQLite database, with **no**
`ABSTRACT_*` API keys configured - the geolocation/holiday enrichment is
skipped and signup still succeeds.

```console
$ python manage.py migrate && python manage.py runserver 8611

# 1. Sign up
$ curl -s -X POST http://localhost:8611/api/signup -H 'Content-Type: application/json' \
    -d '{"email":"ada@example.com","password":"a-Strong-passw0rd","first_name":"Ada","last_name":"Lovelace"}'
{"id":1,"email":"ada@example.com","first_name":"Ada","last_name":"Lovelace","geolocation_data":{},"joined_on_holiday":false}

# 2. Log in and capture the JWT
$ curl -s -X POST http://localhost:8611/api/login -H 'Content-Type: application/json' \
    -d '{"email":"ada@example.com","password":"a-Strong-passw0rd"}'
{"user": {"id": 1, "email": "ada@example.com", "first_name": "Ada", "last_name": "Lovelace", "geolocation_data": {}, "joined_on_holiday": false}, "token": "eyJ0eXAiOiJKV1QiLCJhbGci...<truncated>"}

# 3. Create a post
$ curl -s -X POST http://localhost:8611/api/post -H "Authorization: JWT $TOKEN" \
    -H 'Content-Type: application/json' -d '{"title":"First post","description":"Hello from the API"}'
{"post_data":{"id":1,"title":"First post","description":"Hello from the API","created_at":"2026-09-25T03:24:06.869088Z","updated_at":"2026-09-25T03:24:06.869100Z","user":1}}

# 4. Create a second post, then list them (newest first)
$ curl -s http://localhost:8611/api/post -H "Authorization: JWT $TOKEN"
{"posts":[{"id":2,"title":"Second post","description":"Another one","created_at":"2026-09-25T03:24:06.880889Z","updated_at":"2026-09-25T03:24:06.880900Z","user":1},{"id":1,"title":"First post","description":"Hello from the API","created_at":"2026-09-25T03:24:06.869088Z","updated_at":"2026-09-25T03:24:06.869100Z","user":1}]}

# 5. Like a post
$ curl -s -X PATCH http://localhost:8611/api/post -H "Authorization: JWT $TOKEN" \
    -H 'Content-Type: application/json' -d '{"post_id":"1","action":"like"}'
{"message":"Action performed successfully"}

# 6. Update a post
$ curl -s -X PATCH http://localhost:8611/api/post/1 -H "Authorization: JWT $TOKEN" \
    -H 'Content-Type: application/json' -d '{"title":"First post (edited)"}'
{"post_data":{"id":1,"title":"First post (edited)","description":"Hello from the API","created_at":"2026-09-25T03:24:06.869088Z","updated_at":"2026-09-25T03:24:06.913781Z","user":1}}

# 7. Unauthenticated access is rejected
$ curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8611/api/post
401

# 8. Another user cannot delete this post
$ curl -s -X DELETE http://localhost:8611/api/post/1 -H "Authorization: JWT $OTHER_USER_TOKEN"
{"message":"User is not authenticated/authorized"}

# 9. The owner can
$ curl -s -X DELETE http://localhost:8611/api/post/1 -H "Authorization: JWT $TOKEN"
{"message":"Post successfully deleted"}
```
(eval):65: device not configured: /dev/tty
      52 /Users/dev/Documents/Projects/WAMO/githubs/all_projects/code-samples/TradeCore/docs/api-walkthrough.md
