# AuraStock

Multi-tenant inventory & order management platform for Ethiopia, inspired by Zoho Inventory.

This repo currently contains the **foundation slice**: multi-tenant auth, company/branch
setup, product catalog, and core stock in/out/transfer/adjustment inventory operations.
The full spec (POS, purchasing, sales, accounting, AI forecasting, payment gateway
integrations, etc.) is a large, multi-phase build — this is the base everything else
will be layered onto.

## Structure

- `backend/` — Django + DRF + PostgreSQL + Redis + Celery + Channels (WebSockets)
- `frontend/` — Flutter app (Android, iOS, Web, Desktop) with English, Amharic,
  Afaan Oromo, Tigrigna, and Somali localization

## Running the backend

```
cd backend
python -m venv venv
venv\Scripts\activate       # or source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env      # or cp on macOS/Linux
python manage.py migrate
python manage.py seed_permissions
python manage.py runserver
```

For local development without Docker/Postgres/Redis running, set `USE_SQLITE=True`
in the environment — this swaps in SQLite, an in-memory cache, and an in-memory
channel layer so the whole stack runs with zero external services.

Or via Docker (Postgres + Redis + Django + Celery worker/beat):

```
cd backend
docker compose up --build
```

## Running the frontend

```
cd frontend
flutter pub get
flutter gen-l10n
flutter run -d chrome   # or -d windows / an attached device
```

The app points at `http://127.0.0.1:8000/api/v1` by default (see `lib/core/config/env.dart`).

## What's implemented

- Tenant signup (`POST /api/v1/auth/signup/`) — creates a Company, seeds nine
  starter roles (Owner, Admin, Inventory Manager, Warehouse Manager, Sales Person,
  Cashier, Accountant, Procurement Officer, Delivery Staff) with a permission
  catalog, and creates the first Owner user
- JWT auth (email + password), with automatic access-token refresh in the Flutter app
- Row-level multi-tenant isolation (every tenant-scoped model carries a `company` FK;
  `CompanyScopedViewSet` filters and stamps it automatically)
- Product catalog: categories, brands, units of measure, products, variants,
  auto-generated SKUs (per-company numbering sequences, reusable for invoices/POs later)
- Inventory: warehouses, stock in/out/transfer/adjustment with weighted-average
  costing, insufficient-stock guards, low-stock querying, and full movement history
- Real-time stock updates over WebSocket (JWT-authenticated) for dashboard/warehouse screens
- Flutter: splash/login/signup, responsive dashboard (rail on desktop, bottom nav on
  mobile), product list + add-product, inventory stock levels/history with stock
  action sheets, settings (language switch, theme, logout)

## Known gaps (not yet built)

Sales, POS, purchasing, accounting, reporting/analytics, AI features, customer/supplier
portals, notifications, Ethiopian payment gateway integrations (Telebirr/CBE/M-Pesa/Amole),
and the Ethiopian calendar UI are not implemented yet — they build on this foundation.
