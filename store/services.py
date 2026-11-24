from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from users.models import Address, User

from .models import CartItem, Order, OrderItem


@transaction.atomic
def create_order(*, user: User, address: Address) -> Order:
    # 1. Lock variant rows to prevent concurrent overselling
    cart_items = list(
        CartItem.objects.filter(cart__user=user)
        .select_related("variant", "variant__product")
        .select_for_update()
    )

    if not cart_items:
        raise ValidationError({"detail": "Your cart is empty."})

    # 2. Validate stock for ALL items before creating anything
    for item in cart_items:
        if item.variant.stock < item.quantity:
            raise ValidationError(
                {
                    "detail": f"Insufficient stock for {item.variant}. "
                    f"Available: {item.variant.stock}, requested: {item.quantity}."
                }
            )

    order = Order.objects.create(
        user=user,
        shipping_address=address.get_full_address,
    )

    # 4. Build OrderItems (with price snapshot) and decrement stock
    order_items = []
    for item in cart_items:
        order_items.append(
            OrderItem(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                product_name=item.variant.product.name,
                product_size=item.variant.size,
                unit_price=item.variant.price,
            )
        )
        # Atomic DB-level decrement
        item.variant.stock = F("stock") - item.quantity
        item.variant.save(update_fields=["stock"])

    OrderItem.objects.bulk_create(order_items)

    # 5. Create pay link for the order

    # 6. Clear the user's cart
    CartItem.objects.filter(cart__user=user).delete()

    return order
