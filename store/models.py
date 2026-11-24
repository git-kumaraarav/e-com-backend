import time
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify


class SizeVariant(models.Model):
    product = models.ForeignKey(
        "Product", related_name="size_variants", on_delete=models.CASCADE
    )
    stock = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=50, default="Free Size")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("99999999.00")
    )

    class Meta:
        unique_together = ("product", "size")

    def __str__(self) -> str:
        return f"{self.size} - ${self.price}"


class Product(models.Model):
    @staticmethod
    def slugify_name(name: str) -> str:
        return slugify(name) + "-" + str(int(time.time()))

    related_variants = models.ManyToManyField(
        "self", blank=True
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    attributes = models.JSONField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs) -> None:
        is_new = self.pk is None
        if not self.slug:
            self.slug = self.slugify_name(self.name)

        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                transaction.on_commit(self._ensure_default_variant)

    def _ensure_default_variant(self) -> None:
        if not self.size_variants.exists():
            SizeVariant.objects.create(product=self)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self) -> Decimal:
        return Decimal("0.00") + sum(self.items.subtotal for item in self.items.all())

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        SizeVariant, on_delete=models.SET_NULL, related_name="order_item", null=True
    )

    # freeze the product name at the time of order to avoid issues if the product name changes later
    product_name = models.CharField(max_length=200)
    product_size = models.CharField(max_length=50, default="Free Size")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self) -> Decimal:
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs) -> None:
        if not self.product_name:
            self.product_name = self.variant.product.name
        if not self.product_size:
            self.product_size = self.variant.size
        if not self.unit_price:
            self.unit_price = self.variant.price
        super().save(*args, **kwargs)


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        SizeVariant, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "variant")

class WishList(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="wishlist_items"
    )
    added_at = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ("-created_at",)


class EventSaleBanner(models.Model):
    title = models.CharField(max_length=200)
    altText = models.CharField(max_length=300, blank=True)
    imageUrl = models.ImageField(upload_to="event_banners/")
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-starts_at",)

    def __str__(self) -> str:
        return self.title


class InstagramPost(models.Model):
    insta_id = models.CharField(max_length=255, unique=True)
    caption = models.TextField(blank=True, null=True)
    media_type = models.CharField(max_length=50)
    media_url = models.URLField(max_length=1000)
    thumbnail_url = models.URLField(max_length=1000, blank=True, null=True)
    permalink = models.URLField(max_length=1000)
    timestamp = models.DateTimeField()

    def __str__(self) -> str:
        return f"Instagram post {self.insta_id}"


class CarouselBanner(models.Model):
    title = models.CharField(max_length=200)
    altText = models.CharField(max_length=300, blank=True)
    imageUrl = models.ImageField(upload_to="banners/")
    url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-starts_at",)

    def __str__(self) -> str:
        return self.title


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent_category = models.ForeignKey(
        "Category", default=None, on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("slug", "name")
