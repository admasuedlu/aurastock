from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.core.test_utils import TenantAPITestCase, make_company
from apps.inventory.models import StockItem
from apps.inventory.services import assemble_bundle
from apps.products.models import BundleComponent, Product, ProductVariant, UnitOfMeasure


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


class BarcodeLookupTests(TenantAPITestCase):
    def test_lookup_by_product_barcode(self):
        self.make_product(name="Widget", sku="W-1", barcode="6001234567890")
        resp = self.client.get("/api/v1/products/lookup/", {"barcode": "6001234567890"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["product"]["sku"], "W-1")
        self.assertIsNone(resp.data["variant_id"])

    def test_lookup_falls_back_to_variant_barcode(self):
        product = self.make_product(name="Shirt", sku="SH-1")
        variant = ProductVariant.objects.create(
            company=self.company, product=product, sku="SH-1-M", barcode="7001112223334",
        )
        resp = self.client.get("/api/v1/products/lookup/", {"barcode": "7001112223334"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["product"]["sku"], "SH-1")
        self.assertEqual(resp.data["variant_id"], str(variant.id))

    def test_unknown_barcode_returns_404(self):
        resp = self.client.get("/api/v1/products/lookup/", {"barcode": "0000000000000"})
        self.assertEqual(resp.status_code, 404)

    def test_missing_barcode_returns_400(self):
        resp = self.client.get("/api/v1/products/lookup/", {"barcode": "  "})
        self.assertEqual(resp.status_code, 400)

    def test_lookup_is_tenant_scoped(self):
        # Another tenant owns this barcode -> not found for us.
        other_company, _ = make_company("Other Co")
        other_uom = UnitOfMeasure.objects.create(company=other_company, name="Piece", symbol="pc")
        Product.objects.create(company=other_company, name="Theirs", sku="T-1",
                               unit=other_uom, barcode="9009009009009")
        resp = self.client.get("/api/v1/products/lookup/", {"barcode": "9009009009009"})
        self.assertEqual(resp.status_code, 404)
