# code-samples

Three separate Django REST Framework projects, each written for its own brief,
kept in one repository so they can be read side by side. **They share no code, no
database and no settings module** — this file is an index, not an architecture
document. Pick a directory, follow its own README, run it on its own.

| Sample | One line | Behind the HTTP layer | Tests |
|---|---|---|---|
| [`TradeCore/`](TradeCore/tradecore) | JWT-authenticated social API — signup, login, posts, likes | PyJWT, a custom `User` manager, optional signup enrichment | 48 |
| [`aviyel/`](aviyel/aviyel_api) | Collect YouTube search results for a keyword, then analyse the CSV | YouTube Data API v3 client + a pure-pandas stats module | 27 |
| [`notification-app/`](notification-app) | Post one message to a category, get one delivery row per subscriber per channel | Subclass-discovery dispatcher registry, React 18 + MUI front-end | 21 + 14 |

Python 3.10 runs all three (Django 4.0 in the first two does not support 3.11+).
Every sample starts with **no API keys set** and no test makes a network call.

---

## TradeCore — JWT social API

Users sign up with an e-mail and password, get a JWT, and own their posts. Two
optional Abstract API lookups can annotate a signup with the caller's
geolocation and whether the date is a public holiday.

```bash
cd TradeCore/tradecore
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver        # routes under http://localhost:8000/api
python manage.py test             # 48 tests
```

Routes (no trailing slashes): `POST /api/signup`, `POST /api/login`,
`GET /api/user/<id>`, `GET|POST|PATCH /api/post`, `PATCH|DELETE /api/post/<id>`.
A real transcript of the whole path, including the 401 and 404 cases, is in
[`TradeCore/docs/api-walkthrough.md`](TradeCore/docs/api-walkthrough.md) —
captured with no API keys configured.

Two things worth opening:

- **`utils/account_utility.py`** holds validation, token issue/verify and the
  enrichment calls, so no view talks to a third party directly. When
  `ABSTRACT_GEOLOCATION_API_KEY` / `ABSTRACT_HOLIDAYS_API_KEY` are unset the
  lookups are skipped rather than attempted — `EnrichmentDisabledTests` patches
  the module's HTTP session and asserts its `get` is never called, which is why
  the suite needs no keys.
- **Listing is capped and joined.** `MAX_POSTS_PER_RESPONSE = 100` in
  `views/post_api_view.py`, and `test_list_query_count_does_not_grow_with_row_count`
  holds the query count at 2 whether the user has 3 posts or 30.

Env vars (all optional, see `.env.example`): `SECRET_KEY`, `DJANGO_DEBUG`,
`ALLOWED_HOSTS`, `ABSTRACT_GEOLOCATION_API_KEY`, `ABSTRACT_HOLIDAYS_API_KEY`,
`ABSTRACT_API_TIMEOUT` (seconds, default 5).

---

## aviyel — YouTube keyword analysis

`POST /analysis/ {"keyword": "..."}` collects videos into
`aviyel_api/input_files/<keyword>.csv`. `GET /analysis/?keyword=...` reads that
file and writes five report CSVs to `output_files/`. Collection needs a key;
analysis does not.

```bash
cd aviyel/aviyel_api
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
curl 'http://localhost:8000/analysis/?keyword=travel'   # no API key needed
python manage.py test             # 27 tests
```

`travel.csv` is committed, so the GET works on a fresh clone:

```console
{"message":"Analysis complete for 'travel'.","videos_analysed":350,"categories":15,
 "files":["number_of_videos.csv","min_max_tag_videos.csv","average_durations.csv",
          "min_max_tag_durations.csv","classified_tags.csv"]}
```

Full run, including the 503 you get without a key and the generated CSV
contents: [`aviyel/docs/analysis-run.md`](aviyel/docs/analysis-run.md).

The split is the point. `services/youtube.py` owns every network call;
`services/statistics.py` imports neither Django nor `requests` and is pure
pandas; `views.py` only does HTTP. That is what makes 27 offline tests possible.
The client batches: `test_video_details_are_requested_in_batches_of_fifty` feeds
it 120 video ids and requires exactly **3** `videos.list` calls, and
`test_category_names_are_deduplicated_before_fetching` feeds 200 repeated
category ids and requires **1** call.

**The committed dataset is not a clean travel sample.** Of its 350 rows only 29
are `Travel & Events`; the largest categories are Entertainment (65), Gaming
(59) and Education (52). It is kept as-is and labelled because regenerating it
needs a `GOOGLE_API_KEY`. Treat it as input data for exercising the analysis
code, not as a result.

Env vars: `SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`, `GOOGLE_API_KEY`
(collection only).

---

## notification-app — fan-out on write

The only sample with a UI. A message is posted to a category; inside one
transaction the manager writes one `Log` row for every user subscribed to both
that category and a given channel, one `bulk_create` per channel. Nothing is
actually delivered — a dispatcher writes a log row, there is no SMS or e-mail
provider behind it.

```bash
# terminal 1 — API
cd notification-app/notificationAPI
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --messages 4    # channels, categories, 3 users, data
python manage.py runserver
python manage.py test                      # 21 tests

# terminal 2 — front-end
cd notification-app/notificationFrontend
npm install && npm start                   # http://localhost:3000
npm run test:ci                            # 14 tests
```

![Add message form](notification-app/docs/screenshots/01-add-message.png)

Categories come from `GET /categories/` rather than hardcoded ids, and the
resulting log is one row per (user, channel) pair:

![Notification log](notification-app/docs/screenshots/04-notification-log.png)

Adding a channel is a subclass and an attribute — `dispatchers()` in
`main/notifications.py` walks the subclass tree recursively, so no registration
call and no change to the manager is needed:

```python
class WebhookDispatcher(NotificationDispatcher):
    channel_name = "Webhook"
```

`test_a_new_subclass_is_picked_up_automatically` and
`test_nested_subclasses_are_found` hold that contract. On the read side,
`test_log_listing_does_not_scale_queries_with_row_count` asserts `GET /logs/`
costs **2 queries at 4 rows and the same 2 at 44 rows** — `select_related` over
`user`, `channel`, `message` and `message.category`, plus page-size pagination,
so the response is a `{count, results}` envelope rather than a bare array.

Routes: `GET /logs/`, `GET /logs/string`, `POST /add/`, `GET /categories/`.
Env vars: API — `SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS`, `PAGE_SIZE`; front-end — `REACT_APP_API_URL`
(defaults to `http://localhost:8000/`).

More detail, including the endpoint table: [`notification-app/README.md`](notification-app/README.md).

---

## Running all four services at once

[`docker-compose.yml`](docker-compose.yml) wires the three backends and the
front-end on host ports 8611–8614.

```bash
docker compose up               # all four
docker compose up tradecore     # or one
```

| tradecore | aviyel | notification-api | notification-frontend |
|---|---|---|---|
| 8611 | 8612 | 8613 | 8614 |

**The images have not been built or booted.** `docker compose config` parses
cleanly and resolves all four services, and that is the only Docker verification
that has been done here.

## Shared tooling

Only three things at the repository root are shared, and none of them is code:
[`pyproject.toml`](pyproject.toml) (black at 88 columns, isort),
[`setup.cfg`](setup.cfg) (pycodestyle) and `.editorconfig`. Migrations are
excluded from both formatters.

```bash
black .          # from the repository root, covers all three samples
pycodestyle .
```

## What is not here

- **No CI.** The four suites above are run by hand.
- **SQLite and `runserver` everywhere.** These are reading samples, not
  deployments.
- **No queue.** The notification fan-out happens synchronously inside the
  request. Fine at demo scale, wrong for real delivery.
- **`aviyel` loads the whole CSV into memory.** Fine for hundreds of rows.
- **TradeCore pins PyJWT 1.7.1 and `djangorestframework-jwt`**, both
  unmaintained. Upgrading would change the token format and the documented API
  contract, so the pins stand. (`djangorestframework-simplejwt` is installed but
  unused.)
- **No AI features and no added product features.** Each sample answers its
  original brief; anything more would make it harder to assess, not easier.
