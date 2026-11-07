import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.dateparse import parse_datetime

from .models import InstagramPost


class InstagramAPIError(RuntimeError):
    """Raised when Instagram cannot return a usable media response."""


def fetch_instagram_posts(limit: int = 12) -> int:
    token = settings.INSTA_LONG_LIVED_TOKEN
    if not token:
        raise ImproperlyConfigured("INSTA_LONG_LIVED_TOKEN is not configured.")

    response = requests.get(
        "https://graph.instagram.com/me/media",
        params={
            "fields": (
                "id,caption,media_type,media_url,thumbnail_url,"
                "permalink,timestamp"
            ),
            "access_token": token,
            "limit": limit,
        },
        timeout=15,
    )
    try:
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise InstagramAPIError("Instagram media request failed.") from exc
    except ValueError as exc:
        raise InstagramAPIError("Instagram returned invalid JSON.") from exc

    if payload.get("error"):
        message = payload["error"].get("message", "Instagram API error.")
        raise InstagramAPIError(message)

    posts = payload.get("data")
    if not isinstance(posts, list):
        raise InstagramAPIError("Instagram response did not contain media data.")

    saved = 0
    for item in posts:
        timestamp = parse_datetime(item.get("timestamp", ""))
        required_fields = ("id", "media_type", "media_url", "permalink")
        if not all(item.get(field) for field in required_fields) or timestamp is None:
            raise InstagramAPIError("Instagram returned an incomplete media item.")

        InstagramPost.objects.update_or_create(
            insta_id=item["id"],
            defaults={
                "caption": item.get("caption"),
                "media_type": item["media_type"],
                "media_url": item["media_url"],
                "thumbnail_url": item.get("thumbnail_url"),
                "permalink": item["permalink"],
                "timestamp": timestamp,
            },
        )
        saved += 1

    return saved
