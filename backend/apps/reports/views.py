from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Max, Sum
from django.db.models.functions import TruncDate
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasModulePermission
from apps.inventory.models import StockItem, StockMovement
from apps.pos.models import POSTransaction, POSTransactionItem
from apps.products.models import Product
from apps.purchasing.models import GoodsReceiptItem
from apps.sales.models import Invoice, InvoiceItem

from .exporters import maybe_csv

_SALE_INVOICE_STATUSES = [Invoice.Status.CONFIRMED, Invoice.Status.PARTIALLY_PAID, Invoice.Status.PAID]

_MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)
_COST_FIELD = DecimalField(max_digits=20, decimal_places=4)


def _parse_date(value, default):
    if not value:
        return default
    return date.fromisoformat(value)


def _q2(value: Decimal) -> Decimal:
    """Round a money figure to 2 places for a clean response."""
    return value.quantize(Decimal("0.01"))


def _line_revenue_expr():
    """Discount-aware line revenue (quantity * unit_price * (1 - discount%)),
    computed at the DB so it can be Sum()'d -- the line's `line_subtotal` is a
    Python @property and can't be aggregated. Shared by top-products and ABC."""
    return ExpressionWrapper(
        F("quantity") * F("unit_price") * (1 - F("discount_percent") / Decimal("100")),
        output_field=_MONEY_FIELD,
    )


class _ReportView(APIView):
    """Base for all reporting endpoints. Guards them behind the `reports`
    module so only roles granted `reports.view` (Owner, Admin, and the
    managers) can read them -- reports expose company-wide sales, cost, and
    valuation figures, so they shouldn't be open to every authenticated user."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    permission_module = "reports"


class SalesSummaryView(_ReportView):
    """Combines Invoice (confirmed and later) and completed POS transactions
    -- the two things that actually represent a sale in this system -- into
    one revenue picture. Powers the dashboard's Today's Sales / Monthly
    Revenue cards and a daily trend series for charting."""

    def get(self, request):
        company = request.user.company
        days = int(request.query_params.get("days", 30))
        today = date.today()
        start = today - timedelta(days=days - 1)

        invoices = Invoice.objects.filter(company=company, status__in=_SALE_INVOICE_STATUSES, issue_date__gte=start)
        pos_transactions = POSTransaction.objects.filter(
            company=company, status=POSTransaction.Status.COMPLETED, created_at__date__gte=start,
        )

        daily = defaultdict(Decimal)
        for row in invoices.values("issue_date").annotate(total=Sum("total")):
            daily[row["issue_date"]] += row["total"]
        for row in pos_transactions.annotate(day=TruncDate("created_at")).values("day").annotate(total=Sum("total")):
            daily[row["day"]] += row["total"]

        series = [{"date": d.isoformat(), "total": daily.get(d, Decimal("0"))} for d in
                  (start + timedelta(days=i) for i in range((today - start).days + 1))]

        today_total = daily.get(today, Decimal("0"))
        month_start = today.replace(day=1)
        month_total = sum((amount for d, amount in daily.items() if d >= month_start), Decimal("0"))

        export = maybe_csv(request, "sales-summary.csv", [("date", "Date"), ("total", "Total")], series)
        if export is not None:
            return export

        return Response({
            "today_total": today_total,
            "month_total": month_total,
            "period_total": sum(daily.values(), Decimal("0")),
            "series": series,
        })


class TopProductsView(_ReportView):
    """Best sellers by revenue, combining invoice and POS line items over a
    date range (defaults to the last 30 days)."""

    def get(self, request):
        company = request.user.company
        end = _parse_date(request.query_params.get("end"), date.today())
        start = _parse_date(request.query_params.get("start"), end - timedelta(days=29))
        limit = int(request.query_params.get("limit", 10))

        revenue_expr = _line_revenue_expr()

        invoice_rows = InvoiceItem.objects.filter(
            company=company, invoice__status__in=_SALE_INVOICE_STATUSES,
            invoice__issue_date__gte=start, invoice__issue_date__lte=end,
        ).values("product").annotate(qty=Sum("quantity"), revenue=Sum(revenue_expr))

        pos_rows = POSTransactionItem.objects.filter(
            company=company, transaction__status=POSTransaction.Status.COMPLETED,
            transaction__created_at__date__gte=start, transaction__created_at__date__lte=end,
        ).values("product").annotate(qty=Sum("quantity"), revenue=Sum(revenue_expr))

        totals = defaultdict(lambda: {"qty": Decimal("0"), "revenue": Decimal("0")})
        for row in list(invoice_rows) + list(pos_rows):
            totals[row["product"]]["qty"] += row["qty"]
            totals[row["product"]]["revenue"] += row["revenue"]

        top = sorted(totals.items(), key=lambda kv: kv[1]["revenue"], reverse=True)[:limit]
        product_ids = [pid for pid, _ in top]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}

        rows = [
            {
                "product_id": str(pid), "product_name": products[pid].name if pid in products else "Unknown",
                "product_sku": products[pid].sku if pid in products else "",
                "quantity_sold": data["qty"], "revenue": data["revenue"],
            }
            for pid, data in top
        ]
        export = maybe_csv(request, "top-products.csv", [
            ("product_name", "Product"), ("product_sku", "SKU"),
            ("quantity_sold", "Qty sold"), ("revenue", "Revenue"),
        ], rows)
        if export is not None:
            return export
        return Response({"start": start.isoformat(), "end": end.isoformat(), "rows": rows})


class InventoryValuationView(_ReportView):
    def get(self, request):
        company = request.user.company
        stock_items = StockItem.objects.filter(company=company, quantity_on_hand__gt=0).select_related(
            "product", "warehouse",
        )

        value_expr = ExpressionWrapper(F("quantity_on_hand") * F("average_cost"), output_field=_MONEY_FIELD)

        by_warehouse = defaultdict(lambda: Decimal("0"))
        rows = []
        total_value = Decimal("0")
        for item in stock_items:
            value = item.quantity_on_hand * item.average_cost
            total_value += value
            by_warehouse[item.warehouse.name] += value
            rows.append({
                "product_name": item.product.name, "product_sku": item.product.sku,
                "warehouse_name": item.warehouse.name, "quantity_on_hand": item.quantity_on_hand,
                "average_cost": item.average_cost, "value": value,
            })

        rows.sort(key=lambda r: r["value"], reverse=True)
        # CSV export is the whole valuation, not the top-50 the JSON view trims to.
        export = maybe_csv(request, "inventory-valuation.csv", [
            ("product_name", "Product"), ("product_sku", "SKU"), ("warehouse_name", "Warehouse"),
            ("quantity_on_hand", "On hand"), ("average_cost", "Avg cost"), ("value", "Value"),
        ], rows)
        if export is not None:
            return export
        return Response({
            "total_value": total_value,
            "by_warehouse": [{"warehouse_name": name, "value": value} for name, value in by_warehouse.items()],
            "rows": rows[:50],
        })


class DeadStockView(_ReportView):
    """Products still on the shelf with no outbound (sale) movement in the
    given window -- capital sitting idle in inventory."""

    def get(self, request):
        company = request.user.company
        days = int(request.query_params.get("days", 30))
        cutoff = date.today() - timedelta(days=days)

        stock_items = StockItem.objects.filter(company=company, quantity_on_hand__gt=0).select_related(
            "product", "warehouse",
        )

        last_sold = {
            (row["product"], row["variant"], row["warehouse"]): row["last_out"]
            for row in StockMovement.objects.filter(
                company=company, movement_type=StockMovement.MovementType.STOCK_OUT,
            ).values("product", "variant", "warehouse").annotate(last_out=Max("created_at"))
        }

        rows = []
        for item in stock_items:
            key = (item.product_id, item.variant_id, item.warehouse_id)
            last_out = last_sold.get(key)
            if last_out is not None and last_out.date() >= cutoff:
                continue
            rows.append({
                "product_name": item.product.name, "product_sku": item.product.sku,
                "warehouse_name": item.warehouse.name, "quantity_on_hand": item.quantity_on_hand,
                "value": item.quantity_on_hand * item.average_cost,
                "last_sold_at": last_out.isoformat() if last_out else None,
            })

        rows.sort(key=lambda r: r["value"], reverse=True)
        export = maybe_csv(request, "dead-stock.csv", [
            ("product_name", "Product"), ("product_sku", "SKU"), ("warehouse_name", "Warehouse"),
            ("quantity_on_hand", "On hand"), ("value", "Value"), ("last_sold_at", "Last sold"),
        ], rows)
        if export is not None:
            return export
        return Response({"days": days, "rows": rows})


class PurchaseSummaryView(_ReportView):
    """The purchasing mirror of SalesSummaryView. Bases the trend on goods
    receipts valued at their received cost (quantity * unit_cost) rather than
    on purchase orders -- a receipt is the moment goods (and their cost)
    actually enter the business, the same way the sales report counts
    confirmed invoices/POS sales rather than draft quotations."""

    def get(self, request):
        company = request.user.company
        days = int(request.query_params.get("days", 30))
        today = date.today()
        start = today - timedelta(days=days - 1)

        value_expr = ExpressionWrapper(F("quantity") * F("unit_cost"), output_field=_COST_FIELD)
        rows = (
            GoodsReceiptItem.objects.filter(company=company, goods_receipt__received_date__gte=start)
            .values("goods_receipt__received_date")
            .annotate(total=Sum(value_expr))
        )

        daily = defaultdict(Decimal)
        for row in rows:
            daily[row["goods_receipt__received_date"]] += row["total"]

        series = [
            {"date": d.isoformat(), "total": _q2(daily.get(d, Decimal("0")))}
            for d in (start + timedelta(days=i) for i in range((today - start).days + 1))
        ]

        month_start = today.replace(day=1)
        export = maybe_csv(request, "purchase-summary.csv", [("date", "Date"), ("total", "Total")], series)
        if export is not None:
            return export
        return Response({
            "today_total": _q2(daily.get(today, Decimal("0"))),
            "month_total": _q2(sum((amt for d, amt in daily.items() if d >= month_start), Decimal("0"))),
            "period_total": _q2(sum(daily.values(), Decimal("0"))),
            "series": series,
        })


class AbcAnalysisView(_ReportView):
    """Pareto (ABC) classification of products by their revenue contribution
    over a window (defaults to the last 365 days). Products are ranked by
    revenue, and walking down that ranking the running cumulative share of
    total revenue puts each into a class: A up to `a_threshold`% (the vital
    few), B up to `b_threshold`%, C the rest (the trivial many). Only products
    that actually sold in the window are classified."""

    def get(self, request):
        company = request.user.company
        end = _parse_date(request.query_params.get("end"), date.today())
        start = _parse_date(request.query_params.get("start"), end - timedelta(days=364))
        a_threshold = Decimal(request.query_params.get("a_threshold", "80"))
        b_threshold = Decimal(request.query_params.get("b_threshold", "95"))

        revenue_expr = _line_revenue_expr()
        invoice_rows = InvoiceItem.objects.filter(
            company=company, invoice__status__in=_SALE_INVOICE_STATUSES,
            invoice__issue_date__gte=start, invoice__issue_date__lte=end,
        ).values("product").annotate(qty=Sum("quantity"), revenue=Sum(revenue_expr))

        pos_rows = POSTransactionItem.objects.filter(
            company=company, transaction__status=POSTransaction.Status.COMPLETED,
            transaction__created_at__date__gte=start, transaction__created_at__date__lte=end,
        ).values("product").annotate(qty=Sum("quantity"), revenue=Sum(revenue_expr))

        totals = defaultdict(lambda: {"qty": Decimal("0"), "revenue": Decimal("0")})
        for row in list(invoice_rows) + list(pos_rows):
            totals[row["product"]]["qty"] += row["qty"]
            totals[row["product"]]["revenue"] += row["revenue"]

        ranked = sorted(
            ((pid, d) for pid, d in totals.items() if d["revenue"] > 0),
            key=lambda kv: kv[1]["revenue"], reverse=True,
        )
        grand_total = sum((d["revenue"] for _, d in ranked), Decimal("0"))
        products = {p.id: p for p in Product.objects.filter(id__in=[pid for pid, _ in ranked])}

        summary = {c: {"product_count": 0, "revenue": Decimal("0")} for c in ("A", "B", "C")}
        rows = []
        cumulative = Decimal("0")
        for pid, data in ranked:
            revenue = data["revenue"]
            cumulative += revenue
            cum_pct = (cumulative / grand_total * 100) if grand_total else Decimal("0")
            if cum_pct <= a_threshold:
                abc_class = "A"
            elif cum_pct <= b_threshold:
                abc_class = "B"
            else:
                abc_class = "C"
            summary[abc_class]["product_count"] += 1
            summary[abc_class]["revenue"] += revenue
            rows.append({
                "product_id": str(pid),
                "product_name": products[pid].name if pid in products else "Unknown",
                "product_sku": products[pid].sku if pid in products else "",
                "quantity_sold": data["qty"], "revenue": _q2(revenue),
                "cumulative_pct": _q2(cum_pct), "abc_class": abc_class,
            })

        summary_rows = [
            {
                "abc_class": c,
                "product_count": summary[c]["product_count"],
                "revenue": _q2(summary[c]["revenue"]),
                "revenue_pct": _q2(summary[c]["revenue"] / grand_total * 100) if grand_total else Decimal("0"),
            }
            for c in ("A", "B", "C")
        ]
        export = maybe_csv(request, "abc-analysis.csv", [
            ("abc_class", "Class"), ("product_name", "Product"), ("product_sku", "SKU"),
            ("quantity_sold", "Qty sold"), ("revenue", "Revenue"), ("cumulative_pct", "Cumulative %"),
        ], rows)
        if export is not None:
            return export
        return Response({
            "start": start.isoformat(), "end": end.isoformat(),
            "a_threshold": a_threshold, "b_threshold": b_threshold,
            "total_revenue": _q2(grand_total), "summary": summary_rows, "rows": rows,
        })
