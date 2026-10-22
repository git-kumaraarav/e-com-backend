from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Order, OrderItem, Product


@transaction.atomic
def create_order(
    *,
    user: object,
    shipping_address: str,
    items: list[dict[str, object]],
) -> Order:
    order = Order.objects.create(user=user, shipping_address=shipping_address)
    total = Decimal('0')

    for item in items:
        product_id = item['product_id']
        quantity = item['quantity']
        try:
            product = Product.objects.select_for_update().get(pk=getattr(product_id, 'pk', product_id))
        except Product.DoesNotExist as exc:
            raise ValidationError({'items': 'One or more selected products do not exist.'}) from exc
        if not product.is_active:
            raise ValidationError({'items': f'{product.name} is not available.'})
        if product.stock < quantity:
            raise ValidationError({'items': f'Only {product.stock} units of {product.name} remain.'})
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.price,
        )
        product.stock -= quantity
        product.save(update_fields=('stock', 'updated_at'))
        total += product.price * quantity

    order.total = total
    order.save(update_fields=('total',))
    return order
