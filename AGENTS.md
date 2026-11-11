# Project Guidelines

## Architecture

- This is a Django 6.1 and Django REST Framework backend.
- `core/` contains project settings and URL routing.
- `users/` owns the custom user model and authentication endpoints.
- `store/` owns catalog, cart, wishlist, order, banner, review, and Instagram-feed
  functionality.
- API routes are defined in [`core/urls.py`](core/urls.py); preserve the existing
  `/api/` prefix and router naming when adding endpoints.

## Development

- Use the repository virtual environment: `./.venv/bin/python`.
- Run management commands from the repository root, for example:
  `./.venv/bin/python manage.py check`.
- Keep secrets and environment-specific values out of source control. Use
  environment variables for integrations such as the Instagram token.
- Use Django migrations for model changes:
  `./.venv/bin/python manage.py makemigrations` followed by
  `./.venv/bin/python manage.py migrate`.

## Testing

- Run the Django test suite with:
  `./.venv/bin/python manage.py test`.
- Add or update tests alongside changes to `users/` or `store/`.
- Prefer DRF `APITestCase` tests for API behavior, including authentication,
  permissions, response status codes, and response data.

## Conventions

- Use the existing Django and DRF serializers, viewsets, permissions, and router
  patterns before introducing new abstractions.
- Preserve JWT authentication and the default authenticated API behavior configured
  in `core/settings.py`.
- Use `Decimal` for monetary values and enforce authorization at the view or
  permission layer for user-owned resources.
- Keep media uploads under the configured media paths and avoid committing generated
  media, local databases, virtual-environment files, or secrets.