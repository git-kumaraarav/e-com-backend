"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView
from django.conf import settings
from django.conf.urls.static import static

from store.views import (
    CartViewSet,
    OrderViewSet,
    ProductViewSet,
    CarouselBannerViewSet,
    EventSaleBannerViewSet,
    WishListViewset,
    SearchViewSet,
    NewlyLaunched,
    InstagramFeedViewSet,
)
from users.views import (
    LoginView,
    RegisterView,
    UserProfileView,
    OAuthView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("banners", CarouselBannerViewSet, basename="banner")
router.register("event-banners", EventSaleBannerViewSet, basename="event-banner")
router.register("orders", OrderViewSet, basename="order")
router.register("search", SearchViewSet, basename="search")
router.register("newly-launched", NewlyLaunched, basename="newly-launched")
router.register("u/cart-items", CartViewSet, basename="cart-item")
router.register("u/wish-list", WishListViewset, basename="wish-list")
router.register("instagram-feed", InstagramFeedViewSet, basename="instagram-feed")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", UserProfileView.as_view(), name="user-profile"),
    path("api/auth/oauth/", OAuthView.as_view(), name="oauth_login"),
    path("api/", include(router.urls)),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
