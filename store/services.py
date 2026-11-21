from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from .models import CartItem, Order, OrderItem
from .serializers import OrderSerializer


@transaction.atomic
def create_order(*, request: Request) -> Order:
    # 1. Lock variant rows to prevent concurrent overselling
    cart_items = list(
        CartItem.objects.filter(user=request.user)
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

    # 3. Validate and save the Order first so order.id exists
    order_serializer = OrderSerializer(data=request.data, context={"request": request})
    order_serializer.is_valid(raise_exception=True)
    order = order_serializer.save()

    # 4. Build OrderItems (with price snapshot) and decrement stock
    order_items = []
    for item in cart_items:
        order_items.append(
            OrderItem(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=item.variant.price,  # snapshot unit price at checkout
            )
        )
        # Atomic DB-level decrement
        item.variant.stock = F("stock") - item.quantity
        item.variant.save(update_fields=["stock"])

    OrderItem.objects.bulk_create(order_items)

    # 5. Clear the user's cart
    CartItem.objects.filter(user=request.user).delete()

    return order  # type: ignore
