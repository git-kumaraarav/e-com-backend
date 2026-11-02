# Postman Collection & Environment Setup

This directory contains the ready-to-import Postman Collection and Environment for the **Commerce API** (Django REST Framework).

---

## 📁 Files Included

1. **[`commerce_api.postman_collection.json`](./commerce_api.postman_collection.json)**:
   - Full Postman v2.1.0 collection covering all 38 endpoints.
   - Organized into 8 folders:
     - `Authentication` (Register, Login, Token Obtain, Token Refresh, OAuth)
     - `User` (Get profile, Patch profile, Put profile)
     - `Products` (List, Detail by slug, Create with JSON, Create with Image/Multipart, Patch, Delete)
     - `Sale banners` (List, Detail, Create Multipart, Patch, Delete)
     - `Event sale banners` (List, Detail, Create Multipart, Patch, Delete)
     - `Cart` (List, Detail, Add item, Update quantity, Remove item)
     - `Wish list` (List, Detail, Add item, Remove item)
     - `Orders` (Create order, List my orders, Detail, Update status, Delete)
2. **[`commerce_api.postman_environment.json`](./commerce_api.postman_environment.json)**:
   - Pre-configured environment variables for local development (`http://127.0.0.1:8000`).
3. **[`ecommerce-api.postman_collection.final.json`](./ecommerce-api.postman_collection.final.json)**:
   - Mirrored updated collection for backwards compatibility.

---

## 🚀 How to Import into Postman

1. Open **Postman**.
2. Click **Import** (top left).
3. Drag & drop or select:
   - `postman/commerce_api.postman_collection.json`
   - `postman/commerce_api.postman_environment.json`
4. Select the **Commerce API (Local)** environment in the top-right environment selector.

---

## 🔑 Authentication Workflow

1. Start your local Django development server:
   ```bash
   python manage.py runserver
   ```
2. In Postman, open the collection and navigate to **Authentication > Login**.
3. Click **Send**.
4. The post-response test script **automatically extracts** `access` and `refresh` tokens and sets them to `{{access_token}}` and `{{refresh_token}}`.
5. All authenticated requests in the collection automatically inherit Bearer authentication using `{{access_token}}`.

---

## 💡 Smart Variable Capture

The collection includes automated test scripts compatible with Django's `CoreRenderer`:
- **Login / Token Obtain**: Stores `access_token` and `refresh_token`.
- **Token Refresh**: Automatically updates `access_token`.
- **List / Create Products**: Automatically extracts and updates `product_slug` and `product_id`.
- **Cart / Wish List**: Automatically updates `cart_item_id` and `wishlist_item_id`.
- **Orders**: Automatically captures `order_id` after order creation.
- **Banners / Event Banners**: Automatically captures `banner_id` and `event_banner_id`.
