from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Max, Sum
from django.db.models.functions import TruncDate
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import StockItem, StockMovement
from apps.pos.models import POSTransaction, POSTransactionItem
from apps.products.models import Product
from apps.sales.models import Invoice, InvoiceItem

_SALE_INVOICE_STATUSES = [Invoice.Status.CONFIRMED, Invoice.Status.PARTIALLY_PAID, Invoice.Status.PAID]

_MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)


def _parse_date(value, default):
    if not value:
        return default
    return date.fromisoformat(value)


class SalesSummaryView(APIView):
    """Combines Invoice (confirmed and later) and completed POS transactions
    -- the two things that actually represent a sale in this system -- into
    one revenue picture. Powers the dashboard's Today's Sales / Monthly
    Revenue cards and a daily trend series for charting."""

    permission_classes = [IsAuthenticated]

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

        return Response({
            "today_total": today_total,
            "month_total": month_total,
            "period_total": sum(daily.values(), Decimal("0")),
            "series": series,
        })


class TopProductsView(APIView):
    """Best sellers by revenue, combining invoice and POS line items over a
    date range (defaults to the last 30 days)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = request.user.company
        end = _parse_date(request.query_params.get("end"), date.today())
        start = _parse_date(request.query_params.get("start"), end - timedelta(days=29))
        limit = int(request.query_params.get("limit", 10))

        revenue_expr = ExpressionWrapper(
            F("quantity") * F("unit_price") * (1 - F("discount_percent") / Decimal("100")),
            output_field=_MONEY_FIELD,
        )

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
        return Response({"start": start.isoformat(), "end": end.isoformat(), "rows": rows})


class InventoryValuationView(APIView):
    permission_classes = [IsAuthenticated]

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
        return Response({
            "total_value": total_value,
            "by_warehouse": [{"warehouse_name": name, "value": value} for name, value in by_warehouse.items()],
            "rows": rows[:50],
        })


class DeadStockView(APIView):
    """Products still on the shelf with no outbound (sale) movement in the
    given window -- capital sitting idle in inventory."""

    permission_classes = [IsAuthenticated]

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
        return Response({"days": days, "rows": rows})
