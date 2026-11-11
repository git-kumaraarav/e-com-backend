from django.contrib import admin

from .models import (
    EventSaleBanner,
    Order,
    OrderItem,
    Product,
    CarouselBanner,
    WishList,
    CartItem,
    Review,
    SizeVariant,
)

admin.site.register(
    (
        Product,
        CarouselBanner,
        Order,
        OrderItem,
        WishList,
        CartItem,
        Review,
        EventSaleBanner,
        SizeVariant,
    )
)
