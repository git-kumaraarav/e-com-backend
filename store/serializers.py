from typing import Any

from rest_framework import serializers

from users.models import Address

from .models import (
    CarouselBanner,
    Cart,
    CartItem,
    EventSaleBanner,
    Order,
    OrderItem,
    Product,
    Review,
    SizeVariant,
    WishList,
)
from .services.create_order import create_order


class CartItemSerializer(serializers.ModelSerializer):
    item_details = serializers.SerializerMethodField(read_only=True)

    def get_item_details(self, obj: CartItem) -> dict[str, object]:
        return {
            "id": obj.variant.id,
            "product_id": obj.variant.product.id,
            "name": obj.variant.product.name,
            "slug": obj.variant.product.slug,
            "image": obj.variant.product.image.url
            if obj.variant.product.image
            else None,
            "size": obj.variant.size,
            "unit_price": obj.variant.price,
            "quantity": obj.quantity,
        }

    class Meta:
        model = CartItem
        fields = ("id", "item_details")
        read_only_fields = ("id", "item_details")


class CartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    items = CartItemSerializer(many=True, read_only=True)
    add_item = serializers.PrimaryKeyRelatedField(
        queryset=SizeVariant.objects.all(),
        write_only=True,
        required=False,
    )

    quantity = serializers.IntegerField(write_only=True, required=False, default=1)

    class Meta:
        model = Cart
        fields = ("user", "items", "add_item", "quantity")
        read_only_fields = ("items",)

    def create(self, validated_data):
        product = validated_data.pop("add_item", None)
        quantity = validated_data.pop("quantity", 1)
        user = validated_data["user"]

        cart, _ = Cart.objects.get_or_create(user=user)
        if product:
            self._upsert_item(cart, product, quantity)
        return cart

    def update(self, instance, validated_data):
        variant = validated_data.pop("add_item", None)
        quantity = validated_data.pop("quantity", 1)

        # if quantity is 0, remove the item from the cart
        if variant and quantity == 0:
            CartItem.objects.filter(cart=instance, variant=variant).delete()

        if variant:
            self._upsert_item(instance, variant, quantity)
        return instance

    def _upsert_item(self, cart, variant, quantity):
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity = quantity
            cart_item.save()


class SizeVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeVariant
        fields = ("id", "stock", "size", "price")


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class ProductVariantSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="product-detail", lookup_field="slug"
    )

    class Meta:
        model = Product
        fields = ("id", "name", "slug", "url")
        read_only_fields = ("id", "name", "slug", "url")


class ProductSerializer(serializers.ModelSerializer):
    related_variants = ProductVariantSerializer(many=True, read_only=True)
    size_variants = SizeVariantSerializer(many=True, read_only=True)

    related_variant_ids = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="related_variants",
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "slug")


class CarouselBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarouselBanner
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
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), write_only=True
    )

    variant = serializers.PrimaryKeyRelatedField(
        queryset=SizeVariant.objects.all(), write_only=True
    )

    class Meta:
        model = OrderItem
        fields = "__all__"
        read_only_fields = (
            "id",
            "order",
            "variant",
            "product_name",
            "product_size",
            "unit_price",
            "quantity",
            "subtotal",
        )


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = (
            "id",
            "status",
            "items",
            "subtotal",
            "shipping_address",
            "created_at",
            "updated_at",
        )


class CheckoutSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), write_only=True, required=True
    )

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = (
            "id",
            "remote_order_id",
            "remote_payment_id",
            "remote_payment_signature",
            "status",
            "is_paid",
            "subtotal",
            "shipping_address",
            "created_at",
            "updated_at",
        )

    def validate_address(self, address: Address) -> Address:
        if address.user != self.context["request"].user:
            raise serializers.ValidationError(
                {"address": "Address does not belong to the user."}
            )
        return address

    def create(self, validated_data: dict[str, Any]) -> Order:
        validated_data.pop("user", None)
        address = validated_data.pop("address")
        return create_order(user=self.context["request"].user, address=address)


class EventSaleBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSaleBanner
        fields = (
            "id",
            "title",
            "imageUrl",
            "url",
            "altText",
            "description",
            "starts_at",
            "ends_at",
        )
        read_only_fields = ("id",)


class WishListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = WishList
        fields = "__all__"
        read_only_fields = ("id", "added_at")


class PaymentVerificationSerializer(serializers.Serializer):
    order_id = serializers.CharField(required=True)
    razorpay_payment_id = serializers.CharField(required=True)
    razorpay_signature = serializers.CharField(required=True)