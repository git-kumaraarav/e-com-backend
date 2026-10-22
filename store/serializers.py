from django.utils import timezone
from rest_framework import serializers
from store.models import CartItem
from .models import (
    SaleBanner, 
    Product, 
    OrderItem, 
    CartItem,
    WishList, 
    Order, 
    Review,
    EventSaleBanner
)
from .services import create_order

class WishListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishList
        fields = "__all__"
        read_only_fields = ("id", "added_at")

class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = "__all__"
        read_only_fields = ("id",)

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ("id", "created_at")

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class SaleBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleBanner
        fields = "__all__"
        read_only_fields = ("id", "created_at")

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError(
                {"ends_at": "End time must be after start time."}
            )
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ("product", "product_name", "quantity", "unit_price", "subtotal")
        read_only_fields = ("unit_price", "subtotal")


class OrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
    )
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "status",
            "shipping_address",
            "total",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "total",
            "items",
            "created_at",
            "updated_at",
        )


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderCreateItemSerializer(many=True, min_length=1, write_only=True)

    class Meta:
        model = Order
        fields = ("shipping_address", "items")

    def create(self, validated_data: dict[str, object]) -> Order:
        items = validated_data.pop("items")
        return create_order(
            user=self.context["request"].user, items=items, **validated_data
        )

class EventSaleBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSaleBanner
        fields = ("id", "title", "imageUrl", "url", "altText", "description", "starts_at", "ends_at")
        read_only_fields = ("id",)