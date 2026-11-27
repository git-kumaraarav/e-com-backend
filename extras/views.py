from django.db.models import QuerySet
from django.core.exceptions import ImproperlyConfigured
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InstagramPost
from .serializers import InstagramPostSerializer
from .services.instagram import InstagramAPIError, fetch_instagram_posts


class InstagramFeedSyncView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request):
        try:
            saved_count = fetch_instagram_posts()
        except ImproperlyConfigured as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except InstagramAPIError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message": "Instagram feed synchronized.",
                "saved_count": saved_count,
            },
            status=status.HTTP_200_OK,
        )


class InstagramFeedViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.AllowAny,)
    serializer_class = InstagramPostSerializer

    def get_queryset(self) -> QuerySet[InstagramPost]:  # type: ignore
        queryset = InstagramPost.objects.order_by("-timestamp")
        return queryset[:9] if self.action == "list" else queryset
