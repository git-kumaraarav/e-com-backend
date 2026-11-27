from django.db.models import QuerySet
from rest_framework import permissions, viewsets

from .models import InstagramPost
from .serializers import InstagramPostSerializer


class InstagramFeedViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.AllowAny,)
    serializer_class = InstagramPostSerializer

    def get_queryset(self) -> QuerySet[InstagramPost]:  # type: ignore
        queryset = InstagramPost.objects.order_by("-timestamp")
        return queryset[:9] if self.action == "list" else queryset
