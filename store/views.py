from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework import permissions, views, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from .models import (
    CarouselBanner,
    Cart,
    CartItem,
    EventSaleBanner,
    InstagramPost,
    Order,
    OrderItem,
    Product,
    SizeVariant,
    WishList,
)
from .pagination import CursorPaginationExt
from .permissions import (
    IsAdminOrReadOnly,
    IsAdminOrStaff,
)
from .serializers import (
    CarouselBannerSerializer,
    CartSerializer,
    EventSaleBannerSerializer,
    InstagramPostSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PlaceOrderSerializer,
    ProductSerializer,
    SizeVariantSerializer,
    WishListSerializer,
)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (IsAdminOrReadOnly,)
    lookup_field = "slug"
    pagination_class = CursorPaginationExt

    def get_queryset(self) -> QuerySet[Product]:  # type: ignore
        queryset = Product.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset


class CarouselBannerViewSet(viewsets.ModelViewSet):
    serializer_class = CarouselBannerSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self) -> QuerySet[CarouselBanner]:  # type: ignore
        queryset = CarouselBanner.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset


class OrderViewSet(viewsets.ModelViewSet):
    pagination_class = CursorPaginationExt

    def get_permission_classes(self) -> list[permissions.BasePermission]:  # type: ignore
        if self.action in ["create", "list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [IsAdminOrStaff()]

    def get_queryset(self) -> QuerySet[Order]:  # type: ignore
        queryset = Order.objects.select_related("user").prefetch_related(
            "items__product"
        )
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self) -> type[OrderSerializer | PlaceOrderSerializer]:  # type: ignore
        return PlaceOrderSerializer if self.action == "create" else OrderSerializer

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        order = input_serializer.save()
        output_serializer = OrderSerializer(
            order, context=self.get_serializer_context()
        )
        return Response(output_serializer.data, status=201)


class CartViewSet(viewsets.ModelViewSet):
    pagination_class = CursorPaginationExt
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CartSerializer
    ordering = "pk"

    def get_queryset(self) -> QuerySet[Cart]:  # type: ignore
        return Cart.objects.filter(user=self.request.user).prefetch_related("items")


class WishListViewset(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WishListSerializer
    pagination_class = CursorPaginationExt
    ordering = "-added_at"

    def get_queryset(self) -> QuerySet[WishList]:  # type: ignore
        return WishList.objects.filter(user=self.request.user).select_related("product")


class EventSaleBannerViewSet(viewsets.ModelViewSet):
    serializer_class = EventSaleBannerSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self) -> QuerySet[EventSaleBanner]:  # type: ignore
        queryset = EventSaleBanner.objects.all()
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(is_active=True)
        return queryset


class SizeVariantViewSet(viewsets.ModelViewSet):
    serializer_class = SizeVariantSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self, request: Request) -> QuerySet[SizeVariant]:  # type: ignore
        return SizeVariant.objects.filter(products__is_active=True)


class InstagramFeedViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.AllowAny,)
    serializer_class = InstagramPostSerializer

    def get_queryset(self) -> QuerySet[InstagramPost]:  # type: ignore
        queryset = InstagramPost.objects.order_by("-timestamp")
        return queryset[:9] if self.action == "list" else queryset


class SearchViewSet(viewsets.GenericViewSet):
    permission_classes = (permissions.AllowAny,)
    pagination_class = CursorPaginationExt
    ordering = "-created_at"

    def list(self, request: Request) -> Response:
        query = request.query_params.get("q", "")
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query), is_active=True
        )
        page = self.paginate_queryset(products)
        serializer = ProductSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class NewlyLaunched(viewsets.GenericViewSet):
    permission_classes = (permissions.AllowAny,)
    pagination_class = CursorPaginationExt
    ordering = "-created_at"

    def list(self, request: Request) -> Response:
        products = Product.objects.filter(is_active=True)
        page = self.paginate_queryset(products)
        serializer = ProductSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class OrderHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OrderSerializer
    pagination_class = CursorPaginationExt

    def get_queryset(self) -> QuerySet[Order]:  # type: ignore
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("user")
            .prefetch_related("items__product")
        )


class PlaceOrderViewSet(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PlaceOrderSerializer

    def post(self, request: Request, *args: object, **kwargs: object) -> Response:

        
