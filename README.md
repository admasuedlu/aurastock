# AuraStock

Multi-tenant inventory & order management platform for Ethiopia, inspired by Zoho Inventory.

This repo is being built in phases. **Phase 1 (foundation):** multi-tenant auth,
company/branch setup, product catalog, core stock in/out/transfer/adjustment inventory
operations. **Phase 2 (order management):** customers, suppliers, quotations/sales
orders/invoices/payments, and purchase orders/goods receipts — wired directly into the
Phase 1 inventory engine (confirming an invoice deducts stock, receiving goods adds it).

The full spec (POS, accounting, reporting/analytics, AI forecasting, Ethiopian payment
gateway integrations, notifications, SaaS admin, 150+ screens per the product brief,
etc.) is a large, multi-phase build. Each phase is built with the same rigor as the
last: real backend logic, migrations run and verified, and every flow smoke-tested via
the actual API before moving on — not stub screens wired to fake data.

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
- Customers and suppliers (basic CRM/vendor records with credit limit / payment terms)
- Sales: quotations, sales orders, and invoices with line items, discounts, and tax;
  confirming an invoice deducts stock via the Phase 1 inventory service; payments
  (cash/bank/Telebirr/CBE Pay/M-Pesa/Amole as payment *methods* — gateway integrations
  themselves are not built) track amount paid / balance due and auto-transition invoice status
- Purchasing: purchase orders with line items; goods receipts against a PO (full or
  partial) add stock via the same inventory service and auto-update PO status
  (draft → sent → approved → partially_received → received); over-receiving is blocked
- Flutter: splash/login/signup, responsive dashboard (rail on desktop, bottom nav on
  mobile), product list + add-product, inventory stock levels/history with stock
  action sheets, a Sales section (orders/invoices/customers) with invoice confirm and
  payment actions, a Purchasing section (orders/suppliers) with a receive-goods flow,
  settings (language switch, theme, logout)
- A demo tenant (`demo@aurastock.local` / `DemoPass123!`) seeded with products, stock,
  a completed purchase→receive cycle, and a confirmed/partially-paid invoice, for
  quickly seeing the app with real data instead of an empty state

## Known gaps (not yet built)

POS, accounting (chart of accounts, journal entries, VAT/WHT reports, P&L/balance
sheet), reporting & analytics, AI features (forecasting, anomaly detection), customer/
supplier portals, notifications (SMS/email/push/WhatsApp), actual Ethiopian payment
gateway integrations (Telebirr/CBE Pay/M-Pesa/Amole — currently just selectable payment
*methods*, not live merchant integrations), the Ethiopian calendar UI, purchase
requests/approvals workflow, quotation→sales-order→invoice conversion (each is created
independently for now), and SaaS platform-admin screens are not implemented yet.
