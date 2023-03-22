# TradeCore Group

Part of [`code-samples`](../../README.md). A captured end-to-end transcript of
every endpoint below is in [`docs/api-walkthrough.md`](../docs/api-walkthrough.md).

# Requirements

Python 3.8-3.10 (Django 4.0 does not support 3.11+).

# Setup

```bash
cd TradeCore/tradecore
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional - every value has a working default
python manage.py migrate
python manage.py runserver
```

**No API keys are required.** `SECRET_KEY` falls back to a development value,
and the two Abstract API lookups used at signup are skipped entirely when their
keys are unset - signup still succeeds, with empty `geolocation_data` and
`joined_on_holiday: false`. See the root README's Configuration table.

### API

1. The task is implemented as a simple Django Rest Framework API.
2. The base url is ```http://127.0.0.1:8000/api```
3. API testing tools such as POSTMAN can be used to test the endpoints.

### API ENDPOINTS
1. **Sign Up**: ```http://127.0.0.1:8000/api/signup```
The endpoint accepts a POST request with the following request body as json. Returns **201 Created** on success.
```
{
    "email": "abc@gmail.com",
    "password": "abc123456",
    "first_name": "abc",
    "last_name": "xyz"
}
```

2. **User Data**: ```http://127.0.0.1:8000/api/user/5```
The endpoint accepts a GET request. The integer at the end is the user id. Returns the user data for given id.
3. **Login**: ```http://127.0.0.1:8000/api/login```
The endpoint accepts a POST request with the following request body and params as json.
```
{
    "email": "abc@gmail.com",
    "password": "abc123"
}
```
4. **Create Post**: ```http://127.0.0.1:8000/api/post```
The endpoint accepts a POST request with the following request body and params as json. There must be a 'Authorization' header in request with the following value ```JWT <token>```
The token can be obtained using the Login endpoint
```
{
    "title": "new title",
    "description": "new description"
}
```
5. **Get Posts**: ```http://127.0.0.1:8000/api/post```
The endpoint accepts a GET request. Returns the all the posts for the user for which the token is in the header. There must be a 'Authorization' header in request with the following value ```JWT <token>```
The token can be obtained using the Login endpoint
6. **Delete Post**: ```http://127.0.0.1:8000/api/post/2```
The endpoint accepts a DELETE request. The integer at the end is the id of the post which is to be deleted. There must be a 'Authorization' header in request with the following value ```JWT <token>```
The token can be obtained using the Login endpoint
7. **Update Post**: ```http://127.0.0.1:8000/api/post/2```
The endpoint accepts a PATCH request with the following request body and params as json. The integer at the end is the id of the post for which the data is to be updated. There must be a 'Authorization' header in request with the following value ```JWT <token>```
The token can be obtained using the Login endpoint. Any attribute of post can be updated
```
{
    "title": "updated title",
    "description": "updated description"
}
```
8. **Like/Unlike Post**: ```http://127.0.0.1:8000/api/post```
The endpoint accepts a PATCH request with the following request body and params as json. There must be a 'Authorization' header in request with the following value ```JWT <token>```
The token can be obtained using the Login endpoint. The endpoint is used to like or unlike a post. The post_id is the id of the post which is to be liked/unliked. The action can be any of the two values (like, unlike). The action is taken on the post from the user for which the token is supplied in the header.
```
{
    "post_id": "7",
    "action": "unlike"
}
```

### Notes on status codes

Creating a resource returns **201 Created** (signup and `POST /api/post`).
Validation failures return **400** with a `validation_error` object naming the
offending fields. `GET /api/post` returns at most 100 posts, newest first.

Login is case-insensitive on the email address, matching the model, which
lowercases it on save.

### Testing

```bash
python manage.py test        # 48 tests
```

Every outbound HTTP call is mocked - the suite needs no API key and makes no
network request.

### Formatting

```bash
black .                      # configured in ../../pyproject.toml
```

