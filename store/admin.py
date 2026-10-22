from django.contrib import admin

from .models import (
    EventSaleBanner,
    Order,
    OrderItem,
    Product,
    SaleBanner,
    WishList,
    CartItem,
    Review,
)

admin.site.register(
    (Product, SaleBanner, Order, OrderItem, WishList, CartItem, Review, EventSaleBanner)
)
