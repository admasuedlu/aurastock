from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.notifications.services import notify_low_stock

from .models import Batch, BatchStock, SerialUnit, StockItem, StockMovement


def _get_or_create_stock_item(company, warehouse, product, variant):
    stock_item, _ = StockItem.objects.select_for_update().get_or_create(
        company=company, warehouse=warehouse, product=product, variant=variant,
    )
    return stock_item


def _is_serial_tracked(product) -> bool:
    return product.track_serial


def _is_batch_tracked(product) -> bool:
    """Expiry tracking implies a batch to attach the date to, so either flag
    makes a product batch-tracked -- unless it's serial-tracked, in which case
    per-unit serials take over (the two schemes are mutually exclusive)."""
    return (product.track_batch or product.track_expiry) and not product.track_serial


def _require_whole_quantity(product, quantity):
    if quantity != quantity.to_integral_value():
        raise ValidationError(f"{product.name} is serial-tracked; quantity must be a whole number.")
    return int(quantity)


def _receive_serials(company, warehouse, product, quantity, serial_numbers, reference):
    """Create one IN_STOCK SerialUnit per serial. Requires exactly `quantity`
    distinct serials, none already on record for this product."""
    count = _require_whole_quantity(product, quantity)
    serials = [s.strip() for s in (serial_numbers or []) if s and s.strip()]
    if len(serials) != count:
        raise ValidationError(f"{product.name} needs exactly {count} serial number(s); got {len(serials)}.")
    if len(set(serials)) != len(serials):
        raise ValidationError("Duplicate serial numbers in the request.")
    clashes = SerialUnit.objects.filter(company=company, product=product, serial_number__in=serials)
    if clashes.exists():
        raise ValidationError(f"Serial number(s) already on record: {', '.join(sorted(c.serial_number for c in clashes))}.")
    SerialUnit.objects.bulk_create([
        SerialUnit(company=company, product=product, serial_number=s, warehouse=warehouse,
                   status=SerialUnit.Status.IN_STOCK, reference=reference)
        for s in serials
    ])


def _select_serials(company, warehouse, product, quantity, serial_numbers):
    """Pick the SerialUnits to move out of a warehouse: the explicit ones if
    given (must be in stock here), else the oldest in-stock units (FIFO)."""
    count = _require_whole_quantity(product, quantity)
    in_stock = SerialUnit.objects.select_for_update().filter(
        company=company, warehouse=warehouse, product=product, status=SerialUnit.Status.IN_STOCK,
    )
    explicit = [s.strip() for s in (serial_numbers or []) if s and s.strip()]
    if explicit:
        units = list(in_stock.filter(serial_number__in=explicit))
        found = {u.serial_number for u in units}
        missing = set(explicit) - found
        if missing:
            raise ValidationError(f"Serial(s) not in stock at this warehouse: {', '.join(sorted(missing))}.")
        if len(units) != count:
            raise ValidationError(f"Provide exactly {count} serial number(s) to match the quantity.")
        return units
    units = list(in_stock.order_by("created_at")[:count])
    if len(units) < count:
        raise ValidationError(f"Only {len(units)} serialized unit(s) in stock; need {count}.")
    return units


def _receive_batch(company, warehouse, product, quantity, batch_number, expiry_date) -> Batch:
    """Get-or-create the Batch and add `quantity` to its per-warehouse stock."""
    batch, _ = Batch.objects.get_or_create(
        company=company, product=product, batch_number=batch_number,
        defaults={"expiry_date": expiry_date},
    )
    if expiry_date and batch.expiry_date != expiry_date:
        batch.expiry_date = expiry_date
        batch.save(update_fields=["expiry_date"])
    batch_stock, _ = BatchStock.objects.select_for_update().get_or_create(
        company=company, warehouse=warehouse, product=product, batch=batch,
    )
    batch_stock.quantity_on_hand += quantity
    batch_stock.save(update_fields=["quantity_on_hand"])
    return batch


def _consume_batches_fefo(company, warehouse, product, quantity):
    """Draw `quantity` from a product's batches in a warehouse, earliest expiry
    first (undated batches last). Returns the list of (Batch, qty_consumed)."""
    stocks = list(
        BatchStock.objects.select_for_update()
        .filter(company=company, warehouse=warehouse, product=product, quantity_on_hand__gt=0)
        .select_related("batch")
        .order_by(F("batch__expiry_date").asc(nulls_last=True), "batch__created_at")
    )
    remaining = quantity
    consumed = []
    for batch_stock in stocks:
        if remaining <= 0:
            break
        take = min(batch_stock.quantity_on_hand, remaining)
        batch_stock.quantity_on_hand -= take
        batch_stock.save(update_fields=["quantity_on_hand"])
        remaining -= take
        consumed.append((batch_stock.batch, take))
    if remaining > 0:
        raise ValidationError(
            f"Insufficient batch stock for {product.name}: short by {remaining}."
        )
    return consumed


def _single_batch(consumed):
    """The batch to stamp on a movement -- the one batch consumed, or None if
    FEFO spanned several (the per-batch balances still capture what moved)."""
    return consumed[0][0] if len(consumed) == 1 else None


@transaction.atomic
def stock_in(*, company, warehouse, product, variant=None, quantity, unit_cost=Decimal("0"),
             reference="", reason="", user=None, batch_number=None, expiry_date=None, serial_numbers=None):
    if quantity <= 0:
        raise ValidationError("Quantity must be positive.")

    batch = None
    if _is_serial_tracked(product):
        _receive_serials(company, warehouse, product, quantity, serial_numbers, reference)
    elif _is_batch_tracked(product):
        if not batch_number:
            raise ValidationError(f"{product.name} is batch-tracked; a batch number is required.")
        if product.track_expiry and not expiry_date:
            raise ValidationError(f"{product.name} tracks expiry; an expiry date is required.")
        batch = _receive_batch(company, warehouse, product, quantity, batch_number, expiry_date)

    stock_item = _get_or_create_stock_item(company, warehouse, product, variant)
    existing_value = stock_item.quantity_on_hand * stock_item.average_cost
    incoming_value = quantity * unit_cost
    new_quantity = stock_item.quantity_on_hand + quantity
    stock_item.average_cost = (
        (existing_value + incoming_value) / new_quantity if new_quantity > 0 else unit_cost
    )
    stock_item.quantity_on_hand = new_quantity
    stock_item.save(update_fields=["quantity_on_hand", "average_cost", "updated_at"])

    return StockMovement.objects.create(
        company=company, warehouse=warehouse, product=product, variant=variant,
        movement_type=StockMovement.MovementType.STOCK_IN, quantity=quantity,
        unit_cost=unit_cost, reference=reference, reason=reason, created_by=user, batch=batch,
    )


@transaction.atomic
def stock_out(*, company, warehouse, product, variant=None, quantity, reference="", reason="", user=None,
              serial_numbers=None):
    if quantity <= 0:
        raise ValidationError("Quantity must be positive.")

    stock_item = _get_or_create_stock_item(company, warehouse, product, variant)
    if stock_item.available_quantity < quantity:
        raise ValidationError(
            f"Insufficient stock: available {stock_item.available_quantity}, requested {quantity}."
        )

    # Serial- and batch-tracked goods are drawn automatically (serials FIFO by
    # receipt, batches earliest-expiry-first) so sales/POS/invoice flows call
    # stock_out with no per-unit info and it just works -- they never need to
    # know about serials or batches.
    batch = None
    if _is_serial_tracked(product):
        units = _select_serials(company, warehouse, product, quantity, serial_numbers)
        for unit in units:
            unit.status = SerialUnit.Status.OUT
            unit.warehouse = None
            unit.reference = reference
        SerialUnit.objects.bulk_update(units, ["status", "warehouse", "reference"])
    elif _is_batch_tracked(product):
        batch = _single_batch(_consume_batches_fefo(company, warehouse, product, quantity))

    stock_item.quantity_on_hand -= quantity
    stock_item.save(update_fields=["quantity_on_hand", "updated_at"])

    if stock_item.quantity_on_hand <= stock_item.product.reorder_level:
        notify_low_stock(stock_item=stock_item)

    return StockMovement.objects.create(
        company=company, warehouse=warehouse, product=product, variant=variant,
        movement_type=StockMovement.MovementType.STOCK_OUT, quantity=quantity,
        unit_cost=stock_item.average_cost, reference=reference, reason=reason, created_by=user, batch=batch,
    )


@transaction.atomic
def transfer_stock(*, company, from_warehouse, to_warehouse, product, variant=None,
                    quantity, reference="", reason="", user=None, serial_numbers=None):
    if from_warehouse == to_warehouse:
        raise ValidationError("Source and destination warehouse must differ.")

    source_item = _get_or_create_stock_item(company, from_warehouse, product, variant)
    if source_item.available_quantity < quantity:
        raise ValidationError(
            f"Insufficient stock at {from_warehouse}: available {source_item.available_quantity}, "
            f"requested {quantity}."
        )
    unit_cost = source_item.average_cost

    # Carry the actual serials/batches across so the destination's per-unit and
    # per-batch balances stay correct, not just the aggregate quantity.
    batch = None
    if _is_serial_tracked(product):
        units = _select_serials(company, from_warehouse, product, quantity, serial_numbers)
        for unit in units:
            unit.warehouse = to_warehouse
            unit.reference = reference
        SerialUnit.objects.bulk_update(units, ["warehouse", "reference"])
    elif _is_batch_tracked(product):
        consumed = _consume_batches_fefo(company, from_warehouse, product, quantity)
        for moved_batch, moved_qty in consumed:
            dest_batch_stock, _ = BatchStock.objects.select_for_update().get_or_create(
                company=company, warehouse=to_warehouse, product=product, batch=moved_batch,
            )
            dest_batch_stock.quantity_on_hand += moved_qty
            dest_batch_stock.save(update_fields=["quantity_on_hand"])
        batch = _single_batch(consumed)

    source_item.quantity_on_hand -= quantity
    source_item.save(update_fields=["quantity_on_hand", "updated_at"])

    dest_item = _get_or_create_stock_item(company, to_warehouse, product, variant)
    existing_value = dest_item.quantity_on_hand * dest_item.average_cost
    new_quantity = dest_item.quantity_on_hand + quantity
    dest_item.average_cost = (
        (existing_value + quantity * unit_cost) / new_quantity if new_quantity > 0 else unit_cost
    )
    dest_item.quantity_on_hand = new_quantity
    dest_item.save(update_fields=["quantity_on_hand", "average_cost", "updated_at"])

    out_movement = StockMovement.objects.create(
        company=company, warehouse=from_warehouse, related_warehouse=to_warehouse,
        product=product, variant=variant, movement_type=StockMovement.MovementType.TRANSFER_OUT,
        quantity=quantity, unit_cost=unit_cost, reference=reference, reason=reason, created_by=user, batch=batch,
    )
    StockMovement.objects.create(
        company=company, warehouse=to_warehouse, related_warehouse=from_warehouse,
        product=product, variant=variant, movement_type=StockMovement.MovementType.TRANSFER_IN,
        quantity=quantity, unit_cost=unit_cost, reference=reference, reason=reason, created_by=user, batch=batch,
    )
    return out_movement


@transaction.atomic
def adjust_stock(*, company, warehouse, product, variant=None, quantity_delta, reason="", user=None,
                 batch_number=None, expiry_date=None, serial_numbers=None):
    if quantity_delta == 0:
        raise ValidationError("Adjustment quantity cannot be zero.")

    stock_item = _get_or_create_stock_item(company, warehouse, product, variant)
    if quantity_delta < 0 and stock_item.quantity_on_hand + quantity_delta < 0:
        raise ValidationError("Adjustment would result in negative stock.")

    batch = None
    if _is_serial_tracked(product):
        if quantity_delta > 0:
            _receive_serials(company, warehouse, product, quantity_delta, serial_numbers, reason or "Adjustment")
        else:
            units = _select_serials(company, warehouse, product, -quantity_delta, serial_numbers)
            for unit in units:
                unit.status = SerialUnit.Status.OUT
                unit.warehouse = None
                unit.reference = reason or "Adjustment"
            SerialUnit.objects.bulk_update(units, ["status", "warehouse", "reference"])
    elif _is_batch_tracked(product):
        if quantity_delta > 0:
            if not batch_number:
                raise ValidationError(f"{product.name} is batch-tracked; a batch number is required.")
            if product.track_expiry and not expiry_date:
                raise ValidationError(f"{product.name} tracks expiry; an expiry date is required.")
            batch = _receive_batch(company, warehouse, product, quantity_delta, batch_number, expiry_date)
        else:
            batch = _single_batch(_consume_batches_fefo(company, warehouse, product, -quantity_delta))

    stock_item.quantity_on_hand += quantity_delta
    stock_item.save(update_fields=["quantity_on_hand", "updated_at"])

    movement_type = (
        StockMovement.MovementType.ADJUSTMENT_ADD if quantity_delta > 0
        else StockMovement.MovementType.ADJUSTMENT_REMOVE
    )
    return StockMovement.objects.create(
        company=company, warehouse=warehouse, product=product, variant=variant,
        movement_type=movement_type, quantity=abs(quantity_delta),
        unit_cost=stock_item.average_cost, reason=reason, created_by=user, batch=batch,
    )


@transaction.atomic
def assemble_bundle(*, company, warehouse, bundle_product, quantity, user=None):
    """Kitting: build `quantity` of a bundle by consuming its components' stock
    and producing bundle stock. Each component's stock_out uses the normal
    weighted-average (and FEFO if the component is batch-tracked), and the
    bundle is stocked in at the summed component cost -- so a bundle's cost
    reflects what actually went into it. Reuses the same guards as any
    stock_out, so assembling more than the components allow is blocked."""
    if quantity <= 0:
        raise ValidationError("Assembly quantity must be positive.")

    components = list(bundle_product.bundle_components.select_related("component").all())
    if not components:
        raise ValidationError(f"{bundle_product.name} has no components defined; nothing to assemble.")

    reference = f"ASM-{bundle_product.sku}"
    total_cost = Decimal("0")
    for line in components:
        movement = stock_out(
            company=company, warehouse=warehouse, product=line.component,
            quantity=line.quantity * quantity, reference=reference,
            reason=f"Assembly of {bundle_product.sku}", user=user,
        )
        total_cost += movement.quantity * movement.unit_cost

    return stock_in(
        company=company, warehouse=warehouse, product=bundle_product,
        quantity=quantity, unit_cost=total_cost / quantity, reference=reference,
        reason="Assembly", user=user,
    )
