from django.contrib import admin

from .models import (
    EventSaleBanner,
    Order,
    OrderItem,
    Product,
    CarouselBanner,
    WishList,
    Cart,
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
        Cart,
        Review,
        EventSaleBanner,
        SizeVariant,
    )
)
