<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Project Guidelines

## Development workflow

### Validation

- Run `npm run lint` for lint validation.
- Run `npm run build` for type-checking and production-build validation.
- Use `npm run dev` for local development.

### Next.js changes

- Before changing Next.js behavior or conventions, read the relevant guide in `node_modules/next/dist/docs/`.
- Do not remove or edit the generated `nextjs-agent-rules` block above; Next.js may regenerate it.

## Application architecture

- Use the Next.js App Router under `app/`; keep route-specific pages, layouts, and server actions close to their route.
- Organize reusable components under `components/` by domain (`auth`, `cart`, `home`, `layout`, `product`, `shared`, `carousel`).
- Keep presentation in each domain's `ui/` directory and client-side hooks/stateful behavior in its `logic/` directory. Keep reusable visual primitives in `components/ui/`.
- Keep backend calls and server actions in `components/actions/`, shared server-only request handling in `components/utils/`, and application data helpers in `lib/`.

## Code style and error handling

- Use TypeScript and the `@/*` path alias for workspace imports.
- Follow existing Tailwind utility-class and component patterns; reuse components from `components/ui/` before adding new primitives.
- Preserve explicit error handling and user-facing error states. Log unexpected failures with useful context.
- Product cart and wishlist controls should use the shared `useStore()` actions, require authentication through the store, and expose pending and success feedback while asynchronous updates are in flight.
- Keep cart quantities at a minimum of one in product controls; use the shared quantity update action for increments, decrements, and removal.

## Authentication

- Use NextAuth for credentials and Google sign-in; do not call backend authentication endpoints directly from client components.
- Use `getServerSession(authOptions)` for server-side session checks and `getSession()`/`signIn()`/`signOut()` from `next-auth/react` in client components.
- Route backend requests through `components/utils/apiFetch.ts` so the current session access token and unauthorized handling remain consistent.
- Protect authenticated routes through `proxy.ts` and keep callback URLs restricted to same-origin paths.

# API context

The API uses the `/api/` prefix.

## Response and pagination

Successful responses use the global `CoreRenderer` envelope:

- `status`: `true` for 2xx responses and `false` otherwise
- `status_code`: the HTTP status code
- `timestamp`: the response `Date` header, or `null` when unavailable
- `data`: the successful response payload
- `error`: the error response payload

For validation and other errors, read details from `error`, not `data`.
Endpoints that already return an `error` object may produce an object nested
under the renderer's `error` property.

Paginated responses use `CursorPaginationExt`:

- Page size: **10**
- Pagination style: **cursor-based**
- Pagination fields are inside `data`: `next`, `previous`, and `results`
- Follow the returned `next` and `previous` URLs; do not calculate page
  numbers from the cursor

### Paginated response

```json
{
  "status": true,
  "status_code": 200,
  "timestamp": null,
  "data": {
    "next": "http://127.0.0.1:8000/api/products/?cursor=cD0yMDI2LTEwLTIzKzA4JTNBNTclM0EzOC4zNTk3MjklMkIwMCUzQTAw",
    "previous": null,
    "results": [
      {
        "id": 7,
        "name": "Example Product",
        "slug": "example-product-1793693654",
        "related_variants": [
          {
            "id": 1,
            "name": "related product name"
            "slug" : "related-product-name"
            "url": "http://127.0.0.1:8000/api/products/related-product-name/"
          }, 
        ],
        "description": "A product description",
        "image": null,
        "attributes": {
          "color": "blue",
          "size": "80x60x30",
          "fit": "fit"
        },
        "is_active": true,
        "created_at": "2026-11-03T08:14:14.948922Z",
        "updated_at": "2026-11-03T11:31:43.137504Z",
        "size_variants": [
          {
            "size": "28",
            "stock": 20,
            "price": "300.00"
          }
        ]
      }
    ]
  }
}
```

### Non-paginated response

```json
{
  "status": true,
  "status_code": 200,
  "timestamp": null,
  "data": {
    "id": 9,
    "name": "Example Product",
    "slug": "example-product-1794284532",
    "related_variants": [
      {
        "id": 1,
        "name": "related product name"
        "slug" : "related-product-name"
        "url": "http://127.0.0.1:8000/api/products/related-product-name/"
      }, 
    ],
    "description": "A product description",
    "image": null,
    "attributes": {
      "color": "blue"
    },
    "is_active": true,
    "created_at": "2026-11-10T04:22:12.776674Z",
    "updated_at": "2026-11-10T04:22:12.776696Z",
    "size_variants": [
      {
        "size": "28",
        "stock": 20,
        "price": "300.00"
      },
      {
        "size": "30",
        "stock": 20,
        "price": "500.00"
      }
    ]
  }
}
```

### Endpoint pagination

| Category                 | Endpoints                                                                      |
| ------------------------ | ------------------------------------------------------------------------------ |
| Actually paginated       | Products, orders, cart items, wishlist, Instagram feed, Search, newly launched |
| No pagination configured | Banners, event banners, authentication, user profile, OAuth                    |

## Authentication endpoints

Authentication-protected routes require:

```text
Authorization: Bearer <access-token>
```

| Route                      | HTTP method    | Properties                                                                                                                         |
| -------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `/api/auth/register/`      | `POST`         | Request: `name`, `email`, `password`. Response: `id`, `name`, `email`. `password` is write-only and must be at least 8 characters. |
| `/api/auth/login/`         | `POST`         | Request: `email`, `password`. Response: `accessToken`, `refreshToken`, `expires_at`, and `user` (`id`, `email`, `name`).           |
| `/api/auth/token/`         | `POST`         | Request: `email`, `password`. Response: SimpleJWT `access` and `refresh` tokens.                                                   |
| `/api/auth/token/refresh/` | `POST`         | Request: `refreshToken`. Response: `accessToken`, `refreshToken`, `expires_at`; a new refresh token is issued.                    |
| `/api/auth/me/`            | `GET`          | Response: `email`, `name`.                                                                                                         |
| `/api/auth/me/`            | `PUT`, `PATCH` | Writable properties: `email`, `name`.                                                                                              |
| `/api/auth/oauth/`         | `POST`         | Request: `token`, `provider` (`google`, `github`, or `facebook`). Google is currently the implemented provider.                    |

## Catalog and content

### Products

Base route: `/api/products/`

| HTTP method    | URL                     | Properties                                                                                                                                                                           |
| -------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GET`          | `/api/products/`        | Lists active products for regular users.                                                                                                                                             |
| `POST`         | `/api/products/`        | Admin only. Writable: `name`, `description`, `image`, `attributes`, `is_active`, and optional `related_variant_ids` (product IDs). A default `Free Size` variant is created when no size variant exists. `slug` is generated/read-only; `id`, `created_at`, `updated_at`, `related_variants`, and `size_variants` are read-only. |
| `GET`          | `/api/products/<slug>/` | Reads one product by `slug`.                                                                                                                                                         |
| `PUT`, `PATCH` | `/api/products/<slug>/` | Admin only. Updates the writable product properties above. `related_variant_ids` replaces the related-product set when supplied.                                                       |
| `DELETE`       | `/api/products/<slug>/` | Admin only. Deletes a product.                                                                                                                                                       |

Product response properties are `id`, `name`, `slug`, `description`, `image`,
`related_variants`, `size_variants`, `attributes`, `is_active`, `created_at`,
and `updated_at`. `related_variants` contains nested product summaries with
`id`, `name`, `slug`, `related_variants`, and a detail `url`. Each
`size_variants` item contains `size`, `stock`, and decimal-string `price`.
Size variants are not managed by a separate registered API route.

### Banners

| HTTP method    | URL                                                 | Properties                                                                                                                             |
| -------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`          | `/api/banners/` or `/api/banners/<id>/`             | Reads active carousel banners.                                                                                                         |
| `POST`         | `/api/banners/`                                     | Admin only. Writable: `title`, `altText`, `imageUrl`, `url`, `is_active`, `starts_at`, `ends_at`. `id` and `created_at` are read-only. |
| `PUT`, `PATCH` | `/api/banners/<id>/`                                | Admin only. Updates banner properties. `ends_at` must be after `starts_at`.                                                            |
| `DELETE`       | `/api/banners/<id>/`                                | Admin only. Deletes a banner.                                                                                                          |
| `GET`          | `/api/event-banners/` or `/api/event-banners/<id>/` | Reads active event-sale banners.                                                                                                       |
| `POST`         | `/api/event-banners/`                               | Admin only. Writable: `title`, `imageUrl`, `url`, `altText`, `description`, `starts_at`, `ends_at`. `id` is read-only. `is_active` and `created_at` are not exposed by this serializer. |
| `PUT`, `PATCH` | `/api/event-banners/<id>/`                          | Admin only. Updates the exposed event-sale banner properties.                                                                         |
| `DELETE`       | `/api/event-banners/<id>/`                          | Admin only. Deletes an event-sale banner.                                                                                              |

### Instagram feed

| HTTP method | URL                         | Properties                                  |
| ----------- | --------------------------- | ------------------------------------------- |
| `GET`       | `/api/instagram-feed/`      | Publicly reads up to 9 posts, newest first. |
| `GET`       | `/api/instagram-feed/<id>/` | Publicly reads one post.                    |

Instagram post properties are `id`, `insta_id`, `caption`, `media_type`,
`media_url`, `thumbnail_url`, `permalink`, and `timestamp`. This is a
read-only endpoint.

### Search and newly launched products

| HTTP method | URL                     | Query parameters / properties                                                             |
| ----------- | ----------------------- | ----------------------------------------------------------------------------------------- |
| `GET`       | `/api/search/?q=<term>` | Publicly searches active products by `name` or `description`. Returns product properties. |
| `GET`       | `/api/newly-launched/`  | Publicly lists active products ordered by creation date. Returns product properties.      |

## User-owned resources

### Orders

| HTTP method    | URL                 | Properties                                                                                                                                                                                |
| -------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`          | `/api/orders/`      | Authenticated users read their own orders; staff can read all orders.                                                                                                                     |
| `POST`         | `/api/orders/`      | Authenticated users create an order with `shipping_address` and `items`. Each item has `product_id` and `quantity` (minimum 1).                                                           |
| `GET`          | `/api/orders/<id>/` | Reads an order.                                                                                                                                                                           |
| `PUT`, `PATCH` | `/api/orders/<id>/` | Staff/admin order management. The order serializer only permits `shipping_address` to be changed; `id`, `user`, `status`, `total`, `items`, `created_at`, and `updated_at` are read-only. |
| `DELETE`       | `/api/orders/<id>/` | Staff/admin order management.                                                                                                                                                             |

Order response properties are `id`, `user`, `status`, `shipping_address`,
`total`, `items`, `created_at`, and `updated_at`. Each item contains
`product`, `product_name`, `quantity`, `unit_price`, and `subtotal`.

### Cart items

Base route: `/api/u/cart-items/`

| HTTP method    | URL                       | Properties                                                                               |
| -------------- | ------------------------- | ---------------------------------------------------------------------------------------- |
| `GET`          | `/api/u/cart-items/`      | Reads the authenticated user's cart items.                                               |
| `POST`         | `/api/u/cart-items/`      | Creates an item with `product` (product ID) and `quantity`. `user` is assigned from the access token. |
| `GET`          | `/api/u/cart-items/<id>/` | Reads one owned cart item.                                                               |
| `PUT`, `PATCH` | `/api/u/cart-items/<id>/` | Updates `product` and/or `quantity`.                                                     |
| `DELETE`       | `/api/u/cart-items/<id>/` | Deletes an owned cart item.                                                              |

Cart item response properties are `id`, `product`, `quantity`, `created_at`,
and `updated_at`. `user` is accepted internally from the access token and is
not returned by the serializer.

### Wish list

Base route: `/api/u/wish-list/`

| HTTP method    | URL                      | Properties                                                                    |
| -------------- | ------------------------ | ----------------------------------------------------------------------------- |
| `GET`          | `/api/u/wish-list/`      | Reads the authenticated user's wish-list items.                               |
| `POST`         | `/api/u/wish-list/`      | Creates an item with `product`. `user` and `added_at` are assigned/read-only. |
| `GET`          | `/api/u/wish-list/<id>/` | Reads one owned wish-list item.                                               |
| `PUT`, `PATCH` | `/api/u/wish-list/<id>/` | Updates the `product`.                                                        |
| `DELETE`       | `/api/u/wish-list/<id>/` | Deletes an owned wish-list item.                                              |

Wish-list response properties are `id`, `product`, and `added_at`. `user` is
accepted internally from the access token and is not returned by the
serializer.
