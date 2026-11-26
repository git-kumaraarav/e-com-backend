from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView

from store.views import (
    CarouselBannerViewSet,
    CartViewSet,
    CheckoutView,
    EventSaleBannerViewSet,
    InstagramFeedViewSet,
    NewlyLaunched,
    OrderHistoryViewSet,
    ProductViewSet,
    SearchViewSet,
    SizeVariantViewSet,
    VerifyPaymentAPIView,
    WishListViewset,
)
from users.views import (
    AddressListView,
    LoginView,
    OAuthView,
    RegisterView,
    ResendOTPView,
    TokenRefreshView,
    UserProfileView,
    VerifyEmailView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("banners", CarouselBannerViewSet, basename="banner")
router.register("event-banners", EventSaleBannerViewSet, basename="event-banner")
router.register("orders-history", OrderHistoryViewSet, basename="order-history")
router.register("u/cart-items", CartViewSet, basename="cart-item")
router.register("u/wish-list", WishListViewset, basename="wish-list")
router.register("instagram-feed", InstagramFeedViewSet, basename="instagram-feed")
router.register("search", SearchViewSet, basename="search")
router.register("newly-launched", NewlyLaunched, basename="newly-launched")
router.register("size-variants", SizeVariantViewSet, basename="size-variant")
router.register("u/addresses", AddressListView, basename="address-list")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("api/auth/resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", UserProfileView.as_view(), name="user-profile"),
    path("api/auth/oauth/", OAuthView.as_view(), name="oauth_login"),
    path("api/u/checkout/", CheckoutView.as_view(), name="checkout"),
    path(
        "api/u/checkout/verify/",
        VerifyPaymentAPIView.as_view(),
        name="verify-payment",
    ),
    path("api/", include(router.urls)),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
