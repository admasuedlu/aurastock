from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.notifications.services import notify_low_stock

from .models import StockItem, StockMovement


def _get_or_create_stock_item(company, warehouse, product, variant):
    stock_item, _ = StockItem.objects.select_for_update().get_or_create(
        company=company, warehouse=warehouse, product=product, variant=variant,
    )
    return stock_item


@transaction.atomic
def stock_in(*, company, warehouse, product, variant=None, quantity, unit_cost=Decimal("0"),
             reference="", reason="", user=None):
    if quantity <= 0:
        raise ValidationError("Quantity must be positive.")

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
        unit_cost=unit_cost, reference=reference, reason=reason, created_by=user,
    )


@transaction.atomic
def stock_out(*, company, warehouse, product, variant=None, quantity, reference="", reason="", user=None):
    if quantity <= 0:
        raise ValidationError("Quantity must be positive.")

    stock_item = _get_or_create_stock_item(company, warehouse, product, variant)
    if stock_item.available_quantity < quantity:
        raise ValidationError(
            f"Insufficient stock: available {stock_item.available_quantity}, requested {quantity}."
        )
    stock_item.quantity_on_hand -= quantity
    stock_item.save(update_fields=["quantity_on_hand", "updated_at"])

    if stock_item.quantity_on_hand <= stock_item.product.reorder_level:
        notify_low_stock(stock_item=stock_item)

    return StockMovement.objects.create(
        company=company, warehouse=warehouse, product=product, variant=variant,
        movement_type=StockMovement.MovementType.STOCK_OUT, quantity=quantity,
        unit_cost=stock_item.average_cost, reference=reference, reason=reason, created_by=user,
    )


@transaction.atomic
def transfer_stock(*, company, from_warehouse, to_warehouse, product, variant=None,
                    quantity, reference="", reason="", user=None):
    if from_warehouse == to_warehouse:
        raise ValidationError("Source and destination warehouse must differ.")

    source_item = _get_or_create_stock_item(company, from_warehouse, product, variant)
    if source_item.available_quantity < quantity:
        raise ValidationError(
            f"Insufficient stock at {from_warehouse}: available {source_item.available_quantity}, "
            f"requested {quantity}."
        )
    unit_cost = source_item.average_cost
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
        quantity=quantity, unit_cost=unit_cost, reference=reference, reason=reason, created_by=user,
    )
    StockMovement.objects.create(
        company=company, warehouse=to_warehouse, related_warehouse=from_warehouse,
        product=product, variant=variant, movement_type=StockMovement.MovementType.TRANSFER_IN,
        quantity=quantity, unit_cost=unit_cost, reference=reference, reason=reason, created_by=user,
    )
    return out_movement


@transaction.atomic
def adjust_stock(*, company, warehouse, product, variant=None, quantity_delta, reason="", user=None):
    if quantity_delta == 0:
        raise ValidationError("Adjustment quantity cannot be zero.")

    stock_item = _get_or_create_stock_item(company, warehouse, product, variant)
    if quantity_delta < 0 and stock_item.quantity_on_hand + quantity_delta < 0:
        raise ValidationError("Adjustment would result in negative stock.")

    stock_item.quantity_on_hand += quantity_delta
    stock_item.save(update_fields=["quantity_on_hand", "updated_at"])

    movement_type = (
        StockMovement.MovementType.ADJUSTMENT_ADD if quantity_delta > 0
        else StockMovement.MovementType.ADJUSTMENT_REMOVE
    )
    return StockMovement.objects.create(
        company=company, warehouse=warehouse, product=product, variant=variant,
        movement_type=movement_type, quantity=abs(quantity_delta),
        unit_cost=stock_item.average_cost, reason=reason, created_by=user,
    )
