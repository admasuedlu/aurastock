from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.core.test_utils import TenantAPITestCase
from apps.inventory.services import stock_out
from apps.notifications.models import Notification
from apps.notifications.services import scan_overdue_invoices
from apps.sales.models import Invoice


class LowStockNotificationTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.warehouse = self.make_warehouse()
        # reorder_level high enough that any sale drops us to/below it.
        self.product = self.make_product(reorder_level=Decimal("100"))
        self.receive_stock(self.product, self.warehouse, 10, unit_cost="60")

    def _sell_one(self):
        stock_out(company=self.company, warehouse=self.warehouse, product=self.product,
                  quantity=Decimal("1"), reference="POS-1", user=self.user)

    def _low_stock(self):
        return Notification.objects.filter(
            company=self.company, notification_type=Notification.NotificationType.LOW_STOCK)

    def test_selling_below_reorder_level_raises_one_alert(self):
        self._sell_one()
        self.assertEqual(self._low_stock().count(), 1)

    def test_dedupes_while_unread(self):
        self._sell_one()
        self._sell_one()  # still low, prior alert still unread
        self.assertEqual(self._low_stock().count(), 1)

    def test_re_alerts_after_the_first_is_acknowledged(self):
        self._sell_one()
        note = self._low_stock().get()
        note.is_read = True
        note.read_at = timezone.now()
        note.save(update_fields=["is_read", "read_at"])
        self._sell_one()
        self.assertEqual(self._low_stock().count(), 2)  # a fresh one once the old was cleared

    def test_no_alert_when_above_reorder_level(self):
        plenty = self.make_product(sku="PLENTY-1", reorder_level=Decimal("1"))
        self.receive_stock(plenty, self.warehouse, 100, unit_cost="5")
        stock_out(company=self.company, warehouse=self.warehouse, product=plenty,
                  quantity=Decimal("1"), user=self.user)  # 99 left, well above reorder 1
        self.assertEqual(self._low_stock().count(), 0)


class OverdueInvoiceScanTests(TenantAPITestCase):
    def test_scan_flags_overdue_confirmed_invoices(self):
        warehouse = self.make_warehouse()
        customer = self.make_customer()
        product = self.make_product(selling_price="100")
        self.receive_stock(product, warehouse, 10, unit_cost="60")
        invoice = self.client.post("/api/v1/invoices/", {
            "customer": str(customer.id), "warehouse": str(warehouse.id),
            "items": [{"product": str(product.id), "quantity": 1, "unit_price": 100, "tax_percent": 0}],
        }, format="json").data
        self.client.post(f"/api/v1/invoices/{invoice['id']}/confirm/", {}, format="json")

        # Backdate the due date so it's overdue (issue_date is auto today).
        Invoice.objects.filter(id=invoice["id"]).update(
            due_date=timezone.localdate() - timedelta(days=5))

        created = scan_overdue_invoices(company=self.company)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].notification_type, Notification.NotificationType.OVERDUE_INVOICE)
        # Idempotent while unread: a second scan doesn't pile on.
        self.assertEqual(len(scan_overdue_invoices(company=self.company)), 0)
