# E-commerce Backend

Django REST Framework API for an e-commerce application. It provides
authentication, product discovery, shopping cart and wishlist operations,
checkout and order history, and supporting content such as banners and an
Instagram feed.

## Features

- Custom user accounts, email verification, JWT authentication, and OAuth
- Product catalog, search, size variants, and newly launched products
- User cart, wishlist, addresses, checkout, payment verification, and order
  history
- Carousel and event-sale banners
- Cached Instagram feed backed by Instagram Graph API
- Django admin and Celery tasks for background work

## Stack

- Python 3.12 or newer
- Django 6.1 and Django REST Framework
- SQLite for the default database
- Redis for Django cache and Celery broker/backend
- Celery for background tasks

## Project layout

| Path | Responsibility |
| --- | --- |
| `core/` | Django settings, URL routing, response renderer, and Celery setup |
| `users/` | Custom user model, authentication, profile, and address endpoints |
| `store/` | Catalog, cart, wishlist, orders, checkout, and store content |
| `extras/` | Instagram feed model, API, and sync service |
| `postman/` | Postman API collection |
| `deploy/ubuntu.sh` | Ubuntu deployment setup for Gunicorn, Nginx, and Redis |

## Local development

From the repository root, create a virtual environment and install the
dependencies:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

Create a `.env` file in the project root (or set `DJANGO_ENV_FILE` to another
environment file). Django loads this file when settings are initialized. A
minimal local configuration is:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-local-development-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_CACHE_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
```

The application defaults to SQLite at `db.sqlite3`. Redis is expected at
`127.0.0.1:6379` unless the URLs above are changed. Apply migrations, run the
system check, and start Django:

```bash
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py check
./.venv/bin/python manage.py runserver
```

The local API is then available at `http://127.0.0.1:8000/api/`, and Django
admin is at `http://127.0.0.1:8000/admin/`.

### Optional integrations

Set credentials only for integrations enabled in your environment:

| Variables | Used for |
| --- | --- |
| `GOOGLE_CLIENT_ID` | Google OAuth |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay payments |
| `BREVO_API_KEY` | Brevo email integration |
| `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID`, `INSTAGRAM_GRAPH_API_VERSION` | Instagram feed synchronization |

The Instagram Graph API version defaults to `v27.0`. Sync up to 12 items with
`./.venv/bin/python manage.py sync_instagram_posts`; pass `--limit N` to change
the limit. Do not commit `.env` files, API keys, or production secrets.

## API overview

API routes use the `/api/` prefix. Main route groups include:

- Authentication: `/api/auth/`
- Products, search, banners, size variants, and newly launched items
- User cart, wishlist, addresses, checkout, and order history under `/api/u/`
- Public read-only Instagram feed: `/api/instagram-feed/`

JWT authentication uses the `Authorization: Bearer <access-token>` header.
Most endpoints require authentication by default; endpoints that are public
declare their own permissions. Successful and error responses use the common
envelope:

```json
{
  "status": true,
  "status_code": 200,
  "timestamp": "Fri, 27 Nov 2026 07:40:00 GMT",
  "data": {}
}
```

The response `data` contains the endpoint-specific result; errors use `status:
false` and an `error` field. For concrete request examples, import
`postman/e-commerce-api.postman_collection.json` into Postman.

## Tests

Run the Django test suite with:

```bash
./.venv/bin/python manage.py test
```

## Deployment

`deploy/ubuntu.sh` provisions an Ubuntu host with Redis, Gunicorn, Nginx, and
systemd services. From the repository root, run it with a non-root deployment
user and a public domain:

```bash
sudo DEPLOY_USER=<linux-user> DEPLOY_DOMAIN=<domain> bash deploy/ubuntu.sh
```

The script creates `.env.production` if needed and runs Django checks,
migrations, and `collectstatic`. Review the generated environment file and add
the required integration credentials. The script configures HTTP; configure
HTTPS and review Django's production security settings before exposing the
service publicly.
