from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.core.test_utils import TenantAPITestCase
from apps.inventory.models import StockItem
from apps.inventory.services import assemble_bundle
from apps.products.models import BundleComponent, Product


class KittingTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.wh = self.make_warehouse()
        # A gift box = 2 mugs + 1 card.
        self.mug = self.make_product(name="Mug", sku="MUG-1")
        self.card = self.make_product(name="Card", sku="CARD-1")
        self.box = self.make_product(name="Gift Box", sku="BOX-1",
                                     product_type=Product.ProductType.BUNDLE)
        BundleComponent.objects.create(company=self.company, bundle=self.box, component=self.mug,
                                       quantity=Decimal("2"))
        BundleComponent.objects.create(company=self.company, bundle=self.box, component=self.card,
                                       quantity=Decimal("1"))

    def _on_hand(self, product):
        item = StockItem.objects.filter(company=self.company, warehouse=self.wh, product=product).first()
        return item.quantity_on_hand if item else Decimal("0")

    def test_assemble_consumes_components_and_produces_bundle(self):
        self.receive_stock(self.mug, self.wh, 10, unit_cost="4")   # 10 mugs @ 4
        self.receive_stock(self.card, self.wh, 10, unit_cost="1")  # 10 cards @ 1
        # Assemble 3 boxes -> needs 6 mugs + 3 cards.
        assemble_bundle(company=self.company, warehouse=self.wh, bundle_product=self.box,
                        quantity=Decimal("3"), user=self.user)

        self.assertEqual(self._on_hand(self.mug), Decimal("4.000"))   # 10 - 6
        self.assertEqual(self._on_hand(self.card), Decimal("7.000"))  # 10 - 3
        self.assertEqual(self._on_hand(self.box), Decimal("3.000"))

        # Bundle cost = component cost consumed / boxes = (6*4 + 3*1) / 3 = 27/3 = 9.
        box_item = StockItem.objects.get(company=self.company, warehouse=self.wh, product=self.box)
        self.assertEqual(box_item.average_cost, Decimal("9.0000"))

    def test_assemble_blocked_when_components_short(self):
        self.receive_stock(self.mug, self.wh, 1, unit_cost="4")  # not enough mugs
        self.receive_stock(self.card, self.wh, 10, unit_cost="1")
        with self.assertRaises(ValidationError):
            assemble_bundle(company=self.company, warehouse=self.wh, bundle_product=self.box,
                            quantity=Decimal("1"), user=self.user)
        # First component (mug) was short -> whole assembly rolled back, nothing consumed.
        self.assertEqual(self._on_hand(self.card), Decimal("10.000"))
        self.assertEqual(self._on_hand(self.box), Decimal("0"))

    def test_assemble_requires_components(self):
        plain = self.make_product(name="Loose", sku="LOOSE-1")
        with self.assertRaises(ValidationError):
            assemble_bundle(company=self.company, warehouse=self.wh, bundle_product=plain,
                            quantity=Decimal("1"), user=self.user)

    def test_assemble_via_api_and_components_exposed_on_product(self):
        self.receive_stock(self.mug, self.wh, 10, unit_cost="4")
        self.receive_stock(self.card, self.wh, 10, unit_cost="1")
        resp = self.client.post("/api/v1/inventory/assemble/", {
            "warehouse": str(self.wh.id), "bundle_product": str(self.box.id), "quantity": 2,
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._on_hand(self.box), Decimal("2.000"))

        product = self.client.get(f"/api/v1/products/{self.box.id}/").data
        self.assertEqual(len(product["components"]), 2)
