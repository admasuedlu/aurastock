from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncDate
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import StockItem, StockMovement
from apps.products.models import Product

from .statistics_utils import forecast_series, mean_and_stdev, to_float

LEAD_TIME_DAYS = 7
REORDER_HISTORY_DAYS = 30
FORECAST_HISTORY_DAYS = 60
ANOMALY_HISTORY_DAYS = 90
ANOMALY_Z_THRESHOLD = 2.0
MIN_HISTORY_POINTS_FOR_ANOMALY = 5


class ReorderSuggestionsView(APIView):
    """For every (product, warehouse) at or below its reorder point, suggests
    a quantity based on *actual* recent sales velocity -- avg daily demand
    over the last 30 days x a 7-day lead time, plus the product's configured
    safety stock, minus what's already available. Not an arbitrary guess."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = request.user.company
        window_start = date.today() - timedelta(days=REORDER_HISTORY_DAYS)

        sales_by_key = defaultdict(Decimal)
        movements = StockMovement.objects.filter(
            company=company, movement_type=StockMovement.MovementType.STOCK_OUT,
            created_at__date__gte=window_start,
        ).values("product", "variant", "warehouse").annotate(total=Sum("quantity"))
        for row in movements:
            sales_by_key[(row["product"], row["variant"], row["warehouse"])] = row["total"]

        low_stock_items = StockItem.objects.filter(company=company).select_related("product", "warehouse")

        suggestions = []
        for item in low_stock_items:
            if item.quantity_on_hand > item.product.reorder_level:
                continue
            key = (item.product_id, item.variant_id, item.warehouse_id)
            total_sold = sales_by_key.get(key, Decimal("0"))
            avg_daily_sales = total_sold / REORDER_HISTORY_DAYS
            suggested_quantity = (
                avg_daily_sales * LEAD_TIME_DAYS + item.product.safety_stock - item.available_quantity
            )
            if suggested_quantity <= 0:
                continue
            suggestions.append({
                "product_id": str(item.product_id), "product_name": item.product.name,
                "product_sku": item.product.sku, "warehouse_name": item.warehouse.name,
                "available_quantity": item.available_quantity, "reorder_level": item.product.reorder_level,
                "avg_daily_sales": round(avg_daily_sales, 3),
                "lead_time_days": LEAD_TIME_DAYS,
                "suggested_quantity": round(suggested_quantity, 3),
            })

        suggestions.sort(key=lambda s: s["suggested_quantity"], reverse=True)
        return Response({"lead_time_days": LEAD_TIME_DAYS, "history_window_days": REORDER_HISTORY_DAYS,
                          "rows": suggestions})


class DemandForecastView(APIView):
    """Projects daily demand forward using ordinary least-squares linear
    regression on the last 60 days of actual stock-out history for one
    product. A flat/zero history yields a flat/zero forecast -- this isn't
    trying to invent demand that isn't in the data."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = request.user.company
        product_id = request.query_params.get("product")
        if not product_id:
            raise DRFValidationError("product query parameter is required.")
        try:
            product = Product.objects.get(company=company, id=product_id)
        except Product.DoesNotExist as exc:
            raise DRFValidationError("Product not found.") from exc

        forecast_days = int(request.query_params.get("days", 14))
        history_start = date.today() - timedelta(days=FORECAST_HISTORY_DAYS - 1)

        daily_totals = {
            row["day"]: to_float(row["total"])
            for row in StockMovement.objects.filter(
                company=company, product=product, movement_type=StockMovement.MovementType.STOCK_OUT,
                created_at__date__gte=history_start,
            ).annotate(day=TruncDate("created_at")).values("day").annotate(total=Sum("quantity"))
        }

        history_dates = [history_start + timedelta(days=i) for i in range(FORECAST_HISTORY_DAYS)]
        history_series = [daily_totals.get(d, 0.0) for d in history_dates]

        forecast_values = forecast_series(history_series, forecast_days)
        forecast_dates = [date.today() + timedelta(days=i + 1) for i in range(forecast_days)]

        avg_daily_demand = sum(history_series) / len(history_series) if history_series else 0.0
        recent_avg = sum(history_series[-14:]) / min(14, len(history_series)) if history_series else 0.0
        earlier_avg = sum(history_series[:14]) / min(14, len(history_series)) if history_series else 0.0
        if recent_avg > earlier_avg * 1.1:
            trend = "increasing"
        elif recent_avg < earlier_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"

        return Response({
            "product_id": str(product.id), "product_name": product.name,
            "avg_daily_demand": round(avg_daily_demand, 3), "trend": trend,
            "history": [{"date": d.isoformat(), "quantity": q} for d, q in zip(history_dates, history_series)],
            "forecast": [{"date": d.isoformat(), "quantity": round(q, 3)} for d, q in zip(forecast_dates, forecast_values)],
        })


class AnomalyDetectionView(APIView):
    """Flags stock-out movements in the recent window that are statistical
    outliers (more than 2 standard deviations above that product's own
    historical mean) -- a cheap, honest signal for data-entry mistakes,
    shrinkage, or a genuine demand spike worth a human look. Products with
    too little history to make a stdev meaningful are skipped rather than
    flagged on noise."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = request.user.company
        recent_days = int(request.query_params.get("days", 7))
        history_start = date.today() - timedelta(days=ANOMALY_HISTORY_DAYS)
        recent_start = date.today() - timedelta(days=recent_days)

        movements = list(StockMovement.objects.filter(
            company=company, movement_type=StockMovement.MovementType.STOCK_OUT,
            created_at__date__gte=history_start,
        ).select_related("product", "warehouse").order_by("created_at"))

        by_product = defaultdict(list)
        for m in movements:
            by_product[m.product_id].append(m)

        anomalies = []
        for product_id, product_movements in by_product.items():
            quantities = [to_float(m.quantity) for m in product_movements]
            if len(quantities) < MIN_HISTORY_POINTS_FOR_ANOMALY:
                continue
            avg, stdev = mean_and_stdev(quantities)
            if stdev == 0:
                continue
            threshold = avg + ANOMALY_Z_THRESHOLD * stdev

            for m in product_movements:
                if m.created_at.date() < recent_start:
                    continue
                qty = to_float(m.quantity)
                if qty > threshold:
                    anomalies.append({
                        "product_id": str(product_id), "product_name": m.product.name,
                        "warehouse_name": m.warehouse.name, "quantity": qty,
                        "typical_quantity": round(avg, 2), "threshold": round(threshold, 2),
                        "reference": m.reference, "occurred_at": m.created_at.isoformat(),
                    })

        anomalies.sort(key=lambda a: a["occurred_at"], reverse=True)
        return Response({"days": recent_days, "z_threshold": ANOMALY_Z_THRESHOLD, "rows": anomalies})
