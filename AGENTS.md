# Project Guidelines

## Architecture

- This is a Django 6.1 and Django REST Framework backend.
- `core/` contains project settings and URL routing.
- `users/` owns the custom user model and authentication endpoints.
- `store/` owns catalog, cart, wishlist, order, banner, review, and Instagram-feed
  functionality.
- API routes are defined in [`core/urls.py`](core/urls.py); preserve the existing
  `/api/` prefix and router naming when adding endpoints.
- DRF routes use the existing `/api/` prefix. Add or change router registrations in
  `core/urls.py` and keep the existing basename and lookup-field conventions.
- All successful and error JSON responses use `core.renderer.CoreRenderer`:
  `{"status": true, "status_code": 200, "timestamp": null, "data": ...}` or
  `{"status": false, "status_code": 400, "timestamp": null, "error": ...}`.

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
- For paginated discovery endpoints, serialize records with
  `context={"request": request}` when nested hyperlinked fields are present.
- Live-validate route changes with the Django development server and representative
  public and authenticated requests. Keep test credentials separate from source
  data and environment secrets.
- For Postman collection work, use the Postman MCP tools from the start and keep the
  local `postman/e-commerce-api.postman_collection.json` file synchronized with the
  remote `E-Commerce API` collection in the `Aarav Kumar's Workspace`.

## Conventions

- Use the existing Django and DRF serializers, viewsets, permissions, and router
  patterns before introducing new abstractions.
- Preserve JWT authentication and the default authenticated API behavior configured
  in `core/settings.py`.
- Use `Decimal` for monetary values and enforce authorization at the view or
  permission layer for user-owned resources.
- Keep media uploads under the configured media paths and avoid committing generated
  media, local databases, virtual-environment files, or secrets.
- Cart mutations use `SizeVariant` IDs through `add_item` and a quantity. Quantity
  `0` removes that variant from the cart.
- Wish-list records reference a `Product` ID. Address records belong to the
  authenticated user and must be authorized through the user ownership queryset.