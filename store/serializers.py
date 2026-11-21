from rest_framework import serializers

from users.models import Address

from .models import (
    CarouselBanner,
    Cart,
    CartItem,
    EventSaleBanner,
    InstagramPost,
    Order,
    OrderItem,
    Product,
    Review,
    SizeVariant,
    WishList,
)
from .services import create_order


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ("id", "product", "quantity")


class CartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    items = CartItemSerializer(many=True, read_only=True)
    add_item = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
        required=False,
    )
    quantity = serializers.IntegerField(min_value=1, default=1)

    class Meta:
        model = Cart
        fields = ("id", "user", "items", "add_item", "quantity")
        read_only_fields = ("id", "items")

    def create(self, validated_data):
        product = validated_data.pop("add_item", None)
        quantity = validated_data.pop("quantity", 1)
        user = validated_data["user"]

        cart, _ = Cart.objects.get_or_create(user=user)
        if product:
            self._upsert_item(cart, product, quantity)
        return cart

    def update(self, instance, validated_data):
        product = validated_data.pop("add_item", None)
        quantity = validated_data.pop("quantity", 1)

        # if quantity is 0, remove the item from the cart
        if product and quantity == 0:
            CartItem.objects.filter(cart=instance, product=product).delete()

        if product:
            self._upsert_item(instance, product, quantity)
        return instance

    def _upsert_item(self, cart, product, quantity):
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity = quantity
            cart_item.save()


class SizeVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeVariant
        fields = ("stock", "size", "price")


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
        source="order", queryset=Order.objects.all(), write_only=True
    )

    variant = serializers.PrimaryKeyRelatedField(
        source="variant", queryset=SizeVariant.objects.all(), write_only=True
    )

    class Meta:
        model = OrderItem
        fields = "__all__"
        read_only_fields = ("id", "order", "variant", "product_name", "product_size", "unit_price", "quantity", "subtotal")


class HistoryOrderSerializer(serializers.ModelSerializer):
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


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), write_only=True, required=True
    )

    class Meta:
        model = Order
        fields = "__all__" 

    def validate_address(self, address: Address) -> Address:
        if address.user != self.context["request"].user:
            raise serializers.ValidationError(
                {"address": "Address does not belong to the user."}
            )
        return address

    def create(self, validated_data: dict[str, object]) -> Order:
        items = validated_data.pop("items")
        validated_data["shipping_address"] = validated_data.pop(
            "address"
        ).get_full_address()
        return create_order(
            user=self.context["request"].user, items=items, **validated_data
        )


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


class InstagramPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramPost
        fields = "__all__"


class WishListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = WishList
        fields = "__all__"
        read_only_fields = ("id", "added_at")
