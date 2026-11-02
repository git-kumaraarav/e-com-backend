from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import CartItem, Order, Product, CarouselBanner, WishList, EventSaleBanner
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    ProductSerializer,
    CarouselBannerSerializer,
    CartItemSerializer,
    ReviewSerializer,
    WishListSerializer,
    EventSaleBannerSerializer,
)
from .permissions import (
    IsAdminOrReadOnly,
    IsAdminOrStaff,
)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (IsAdminOrReadOnly,)
    lookup_field = "slug"

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
            queryset = queryset.filter(
                is_active=True
            )
        return queryset


class OrderViewSet(viewsets.ModelViewSet):
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

    def get_serializer_class(self) -> type[OrderSerializer | OrderCreateSerializer]:  # type: ignore
        return OrderCreateSerializer if self.action == "create" else OrderSerializer

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        order = input_serializer.save()
        output_serializer = OrderSerializer(
            order, context=self.get_serializer_context()
        )
        return Response(output_serializer.data, status=201)


class CartViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CartItemSerializer

    def get_queryset(self) -> QuerySet[CartItem]:  # type: ignore
        return CartItem.objects.filter(user=self.request.user).select_related("product")


class WishListViewset(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WishListSerializer

    def get_queryset(self) -> QuerySet[WishList]:  # type: ignore
        return WishList.objects.filter(user=self.request.user).select_related("product")


class EventSaleBannerViewSet(viewsets.ModelViewSet):
    serializer_class = EventSaleBannerSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self) -> QuerySet[EventSaleBanner]:  # type: ignore
        queryset = EventSaleBanner.objects.all()
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True 
            )
        return queryset


class SearchViewSet(viewsets.ViewSet):
    permission_classes = (permissions.AllowAny,)

    def list(self, request: Request) -> Response:
        query = request.query_params.get("q", "")
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query), is_active=True
        )
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

