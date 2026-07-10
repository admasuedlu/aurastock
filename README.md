# AuraStock

Multi-tenant inventory & order management platform for Ethiopia, inspired by Zoho Inventory.

This repo is being built in phases. **Phase 1 (foundation):** multi-tenant auth,
company/branch setup, product catalog, core stock in/out/transfer/adjustment inventory
operations. **Phase 2 (order management):** customers, suppliers, quotations/sales
orders/invoices/payments, and purchase orders/goods receipts — wired directly into the
Phase 1 inventory engine (confirming an invoice deducts stock, receiving goods adds it).
**Phase 3 (POS):** till sessions with cash reconciliation, and point-of-sale
transactions with instant stock deduction and refunds — also wired into the same
inventory engine. **Phase 4 (accounting):** a real double-entry ledger, with every
revenue/expense event from Phases 2-3 automatically posting a balanced journal entry —
not a separate, disconnected bookkeeping module. **Phase 5 (reporting & analytics):**
sales trend/top-products/inventory-valuation/dead-stock reports computed live off the
same data, plus wiring the dashboard's Today's Sales and Monthly Revenue cards to real
numbers for the first time (they were a hardcoded 0 placeholder through Phase 1-4,
since there was no sales data yet). **Phase 6 (AI insights):** reorder suggestions,
demand forecasting, and anomaly detection computed with real statistics (least-squares
regression, mean/stdev) over actual sales history — not a call to an external LLM,
which would need credentials this project doesn't have and couldn't be verified
without them. **Phase 7 (notifications):** a Notification model with a real-time
push channel (WebSocket, same JWT-over-query-string pattern as Phase 1's inventory
socket) plus dev-mode email — low-stock alerts fire automatically from the same
`stock_out` choke point every sale already goes through, and overdue-invoice
reminders are raised by a scan endpoint that simulates what a Celery beat schedule
would run periodically (no beat schedule is actually wired up). **Phase 8 (SaaS
platform admin):** a platform-operator layer on top of the tenants — tenant list with
live usage counts, suspend/reactivate that actually locks the tenant out (token
issuance, API access, and WebSockets, not just a status flag), subscription plan
management, and real plan-limit enforcement (users/branches/warehouses) at the
creation choke points. **Phase 9 (customer/supplier portals):** a separate,
non-staff login for external customers and suppliers — signed, expiring tokens
rather than JWTs, since a portal contact modeled as a `User` would inherit that
model's company-wide row visibility — giving customers read access to their
sent quotations (with accept/reject), orders, and invoices, and suppliers
read access to their sent purchase orders (with acknowledge), all wired back
into the Phase 7 notification pipeline so staff hear about portal actions.

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
python manage.py seed_plans
python manage.py runserver
```

To operate the platform itself (tenant list, suspensions, plan management), create
a platform-level admin — tenant signup can't produce one, since it always creates
a company:

```
python manage.py create_platform_admin admin@example.com <password>
```

Logging into the app with that account lands on the platform-admin console instead
of the tenant shell.

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
- Sales: quotations (convertible to a sales order, copying line items and locking the
  quotation as `converted`), sales orders, and invoices with line items, discounts,
  and tax; confirming an invoice deducts stock via the Phase 1 inventory service;
  payments (cash/bank/Telebirr/CBE Pay/M-Pesa/Amole as payment *methods* — gateway
  integrations themselves are not built) track amount paid / balance due and
  auto-transition invoice status
- Purchasing: purchase orders with line items; goods receipts against a PO (full or
  partial) add stock via the same inventory service and auto-update PO status
  (draft → sent → approved → partially_received → received); over-receiving is
  blocked; payments against a PO track amount paid / balance due independently of
  receiving (you can pay a supplier before, during, or after goods arrive);
  overpayment is blocked
- POS: a cashier opens a till session against a warehouse with an opening cash float;
  ringing up a sale deducts stock immediately (no separate confirm step, unlike
  invoices); refunding a completed sale restores stock **at the cost it left at**
  (looked up from the original stock movement, not today's average — so a refund
  doesn't dilute the remaining stock's weighted-average cost); closing a session
  computes expected cash (opening float + completed cash sales) against what the
  cashier counted, surfacing the variance; a cashier can only have one open session
  at a time, and a closed session rejects new sales
- Accounting: a 12-account default chart of accounts (Cash, Bank, Accounts
  Receivable, Inventory, VAT Receivable, Accounts Payable, VAT Payable, Withholding
  Tax Payable, Owner's Equity, Retained Earnings, Sales Revenue, COGS, Operating
  Expenses) seeded on signup. Every one of the following posts a balanced journal
  entry automatically: invoice confirmed (Dr AR / Cr Revenue + VAT Payable), sales
  payment (Dr Cash-or-Bank / Cr AR), goods receipt (Dr Inventory + VAT Receivable /
  Cr AP — booked tax-inclusive so it nets to zero against a later full PO payment),
  PO payment (Dr AP / Cr Cash-or-Bank), POS sale and refund (mirrored pairs), and
  manual expenses (Dr Operating Expenses / Cr Cash-or-Bank). `create_journal_entry`
  rejects any set of lines that doesn't balance, so an unbalanced entry simply
  can't be persisted. Trial balance, P&L, and balance sheet report endpoints read
  straight off the ledger. Verified end-to-end via curl: a full
  PO→receive→pay→sell→POS-sale→POS-refund→expense sequence produces a trial balance
  where total debits exactly equal total credits. Known simplification: there's no
  period-end closing entry yet, so current-period net income sits in the Income/
  Expense accounts rather than being rolled into Retained Earnings — the balance
  sheet endpoint documents this (Assets won't equal Liabilities + Equity until that
  exists), and COGS is never posted (no perpetual cost-of-goods-sold entry on sale),
  so P&L net income is currently gross margin minus operating expenses, not true
  net income.
- Reports: sales summary (today/month/period totals + a daily series, combining
  confirmed-or-later invoices and completed POS transactions — the two things that
  actually represent a sale), top products by revenue (computed via a DB-level F()
  expression replicating the line-item discount math, not a Python property, since
  you can't `Sum()` a `@property`), inventory valuation (`quantity_on_hand *
  average_cost` per product/warehouse, plus totals), and dead stock (on-hand
  products with no `stock_out` movement in N days, found via a single grouped query
  rather than one query per product). All hand-verified against seeded data with
  known-correct expected numbers (e.g. a product sold 5 via invoice + 3 via POS
  shows quantity_sold=8, revenue=8×price).
- AI Insights: reorder suggestions (suggested quantity = 30-day actual sales
  velocity × a 7-day lead time + safety stock − what's available, only for products
  at or below their reorder point — not an arbitrary guess), demand forecasting
  (ordinary least-squares linear regression, pure Python via the stdlib `statistics`
  module, no numpy dependency, on 60 days of stock-out history per product, projected
  forward with a trend label), and anomaly detection (flags stock-out movements more
  than 2 standard deviations above that product's own historical mean — skips
  products with too little history to make a stdev meaningful, rather than flagging
  noise). Verified with seeded, backdated movement history (the API always
  timestamps at "now", so realistic history had to be inserted directly via the ORM):
  a synthetic upward sales trend was correctly detected as "increasing" with a rising
  forecast, and a single planted 60-unit outlier against a ~6-unit baseline was the
  only thing flagged.
- Reports & Insights are reachable via two icons on the dashboard rather than the
  main nav, which was already at 8 destinations.
- Flutter: splash/login/signup, responsive dashboard (rail on desktop, bottom nav on
  mobile, real sales KPIs + a 30-day trend chart), product list + add-product,
  inventory stock levels/history with stock action sheets, a Sales section
  (quotations/orders/invoices/customers) with quotation-to-order conversion and
  invoice confirm/payment actions, a Purchasing section (orders/suppliers) with
  combined receive-goods/record-payment actions, a POS screen (touch-friendly
  product grid, cart, checkout with change-due calculation, today's-sales history
  with refund, shift open/close), an Accounting section (expenses, trial balance,
  P&L, balance sheet), a Reports screen (top products/valuation/dead-stock), an AI
  Insights screen (reorder suggestions/demand forecast chart/anomalies), settings
  (language switch, theme, logout)
- A demo tenant (`demo@aurastock.local` / `DemoPass123!`) can be seeded with sample
  products, stock, a completed purchase→receive cycle, and a confirmed/partially-paid
  invoice — ask to have it recreated, since the dev SQLite database is not persisted
  between sessions
- Notifications: a `Notification` model (company + optional personal `recipient`,
  type, title/message/reference, read state) with a service layer, not a bare CRUD
  resource. `notify_low_stock` is called from `apps/inventory/services.py:stock_out()`
  — the one choke point already shared by the manual inventory stock-out view,
  invoice confirm, and POS checkout — so a low-stock alert fires wherever stock
  actually leaves, without three separate call sites to keep in sync. It dedupes:
  no second unread notification for the same (company, type, reference) while an
  earlier one is still unread, so a slow-selling item doesn't spam one row per sale,
  but it does alert again once the existing one is acknowledged (verified: sold
  below reorder level → 1 notification; sold again while still low → still 1;
  marked read; sold again → a fresh 2nd notification). Overdue-invoice reminders
  come from `scan_overdue_invoices`, exposed as `POST /notifications/scan_overdue/`
  — it simulates what a Celery beat schedule would run periodically (no beat
  schedule is actually wired up); it's addressed to the invoice's `created_by` where
  known rather than broadcast company-wide. Real-time delivery reuses the Phase 1
  JWT-over-query-string WebSocket pattern (`/ws/notifications/`), but with two
  channel groups instead of one: personal notifications go only to a `user-{id}`
  group and company-wide ones (like low stock) go to a `company-{id}` group, so a
  reminder addressed to one salesperson doesn't flash across every other user's
  screen — verified directly against the channel layer (a personal notification
  reached the user's group and did *not* reach the company-wide group). The
  broadcast and email side effects are wrapped in `transaction.on_commit()`, not
  fired inline — `stock_out()` often runs inside an outer `@transaction.atomic`
  block it doesn't own (invoice confirm looping over line items, POS checkout), so
  firing immediately could push a "ghost" notification for a change that a later
  error in the same request then rolls back. Email delivery uses Django's console
  backend in dev (same `LOCAL_DEV_MODE` gating as the SQLite/locmem fallbacks) and
  is real, not mocked; it's genuinely deliverable via SMTP in production once
  `EMAIL_HOST`/credentials are configured. SMS/WhatsApp are **not** built — they'd
  need Twilio/Africa's Talking/Meta Business API credentials this project doesn't
  have, and faking a "sent" response would be worse than not having it; the service
  layer is channel-agnostic, so adding a real provider later is one function plus
  a call from `create_notification`, not a redesign. Flutter: a notification bell
  with an unread-count badge in the dashboard app bar (following the existing
  Reports/Insights icon-button precedent rather than crowding the 8-destination
  main nav further) and a notification center screen that loads via REST and then
  live-updates over the WebSocket.
- SaaS platform admin: platform staff are users with **no** company FK (created via
  `manage.py create_platform_admin`; tenant signup can't produce one), gated by a
  dedicated `IsPlatformAdmin` permission a tenant user can never satisfy regardless
  of their role. Endpoints: platform overview KPIs (tenant/user/signup counts by
  subscription status), tenant list with per-company user/branch/warehouse counts
  (single-query annotations, not N+1), suspend/reactivate, plan CRUD, and
  change-plan. Suspension is enforced in the default JWT **authentication** class
  rather than a permission class — several views set their own
  `permission_classes`, which would silently bypass a default permission — so a
  suspended tenant's users are locked out of every endpoint at once, existing
  tokens included; fresh logins are also refused with a clear message, and the
  WebSocket handshake rejects them too. Verified end-to-end: suspend → the
  tenant's live token 401s and login fails while a second tenant is unaffected →
  reactivate → the same token works again. Plan limits are real, not decorative:
  creating a user/branch/warehouse checks the company's plan cap at the creation
  choke point and 400s with an upgrade message (verified: trial's 1-warehouse cap
  blocked a 2nd warehouse; upgrading to Starter via the change-plan endpoint
  unblocked it; Starter's 5-user cap allowed invites up to exactly 5 and blocked
  the 6th). `seed_plans` seeds Free Trial/Starter/Business/Enterprise tiers
  (idempotent, matches the `trial` code signup auto-assigns). Flutter: logging in
  as platform staff routes to a dedicated platform console (overview KPI tiles,
  company list with search/status chips/suspend/change-plan actions, plan
  editor) — tenant users are hard-redirected away from it and platform staff
  can't wander into tenant screens that assume a company.
- Customer/supplier portal: a `PortalAccount` model that is deliberately **not**
  a `User` — a `User`'s `company` FK is what every staff viewset trusts for row
  visibility, so a customer modeled as a `User` would see the entire tenant's
  data. Portal users authenticate with their own signed, expiring token
  (`Authorization: Portal <token>`, Django `signing`, 12h) via `POST
  /portal/login/`, so staff endpoints reject them by construction (a portal
  token doesn't match the `Bearer` scheme `TenantAwareJWTAuthentication`
  expects). Staff open access from a key-icon action on the customer/supplier
  list (`POST/GET/DELETE /customers/{id}/portal-access/`, same shape for
  suppliers) — scoped to their own tenant since it reuses the same
  `CompanyScopedViewSet.get_object()` every other action on that viewset
  does, so a staff member literally cannot target another tenant's customer.
  This phase also closed a latent Phase 2 gap it made load-bearing: quotations
  and purchase orders have had a `sent` status since Phase 2, but nothing
  could ever transition into it — new `POST /quotations/{id}/send/` and
  `POST /purchase-orders/{id}/send/` staff actions fix that, and they're what
  gates portal visibility (draft documents stay invisible to the portal).
  Customers see their sent-or-later quotations (accept/reject, exactly once —
  a second attempt 400s), sales orders, and confirmed/partially-paid invoices;
  suppliers see sent-or-later purchase orders (acknowledge, which moves
  `sent → approved`, the same status the existing goods-receipt flow already
  expects). Both actions raise a staff notification through the Phase 7
  pipeline, addressed to the document's creator where known. Verified
  end-to-end via curl (30 assertions): visibility rules (draft hidden,
  sent-or-later visible), accept/reject/acknowledge exactly once, every
  cross-auth combination rejected (portal token on staff endpoints 401; staff
  JWT on portal endpoints, wrong-role portal token, and an invalid/expired
  portal token all 403 — authenticated-but-wrong-principal and
  not-authenticated-at-all are deliberately both closed doors, not just one),
  and cross-tenant isolation (another tenant's portal customer 404s fetching
  this tenant's quotation by id, and staff can't grant portal access to
  another tenant's customer — also a 404, same object-scoping mechanism).
  Flutter: a portal login reachable from a link on the staff login screen, a
  portal home (customer: quotations/orders/invoices tabs; supplier: a single
  purchase-orders view) on its own session store and Dio instance so a portal
  token is never confused with a staff JWT, and "Mark as Sent" / "Send to
  Supplier" buttons plus portal-access dialogs wired into the existing
  quotation/PO action sheets and customer/supplier lists. Written to match
  existing conventions exactly and reviewed by hand line-by-line (one real
  bug caught that way: a nullable field read through a non-promoting `if`
  null-check); the Flutter SDK wasn't available in this environment to run
  `flutter analyze`/`test`/`build web`, so unlike the backend this hasn't
  been machine-verified yet.

## Known gaps (not yet built)

Beyond the sales/top-products/valuation/dead-stock reports and the three accounting
reports, there's no purchase-trend report, no ABC analysis, no custom report builder,
and no export to Excel/CSV/PDF. The AI insights are honest statistics on real data, not
a "customer purchase prediction" or "intelligent dashboard" in the fuller sense of the
original spec. Notifications only fire from `stock_out()`, not from `adjust_stock()` or
`transfer_stock()`, so a manual stock adjustment or transfer that drops a product below
its reorder level doesn't raise an alert (a human doing that adjustment already sees
the number they typed); SMS/WhatsApp delivery is architected for but not implemented,
per the note above. Also not built: actual Ethiopian payment
gateway integrations (Telebirr/CBE Pay/M-Pesa/Amole — currently just selectable payment
*methods*, not live merchant integrations), the Ethiopian calendar UI, purchase
requests/approvals workflow, sales-order→invoice conversion (invoices are still created
independently of an order for now), receipt printing / physical cash-drawer /
barcode-scanner hardware integration, offline-mode sync for POS, period-end closing
entries and perpetual COGS posting (see the Accounting simplifications noted above),
and a real Celery beat schedule (the overdue-invoice scan is a POST endpoint that
simulates one, not an actual periodic task). The platform-admin layer manages
subscriptions but doesn't *bill* them — there's no payment collection, invoice
generation for the SaaS fee, or automatic suspension on non-payment (that's the
same missing-payment-gateway problem as the tenant-facing Telebirr integration);
plan limits are enforced only on users/branches/warehouses, not on product counts
or storage; and `past_due`/`cancelled` statuses exist on the model but nothing
transitions companies into them automatically.
