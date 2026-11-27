import re

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.dateparse import parse_datetime

from extras.models import InstagramPost


class InstagramAPIError(RuntimeError):
    """Raised when Instagram cannot return a usable media response."""


def _get_api_configuration() -> tuple[str, str, str]:
    token = settings.INSTAGRAM_SECRET
    if not token:
        raise ImproperlyConfigured(
            "Set INSTAGRAM_ACCESS_TOKEN to a Unified Login system-user access token."
        )

    account_id = settings.INSTAGRAM_ID
    if not account_id:
        raise ImproperlyConfigured(
            "Set INSTAGRAM_ACCOUNT_ID from /me/assigned_instagram_accounts."
        )

    api_version = settings.INSTAGRAM_GRAPH_API_VERSION
    if not re.fullmatch(r"v\d+\.\d+", api_version):
        raise ImproperlyConfigured("INSTAGRAM_GRAPH_API_VERSION is invalid.")
    if not account_id.isdecimal():
        raise ImproperlyConfigured("INSTAGRAM_ACCOUNT_ID must be numeric.")

    return token, account_id, api_version


def _fetch_media_items(
    token: str,
    account_id: str,
    api_version: str,
    limit: int,
) -> list:
    response = requests.get(
        f"https://graph.facebook.com/{api_version}/{account_id}/media",
        params={
            "fields": (
                "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"
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

    media_items = payload.get("data")
    if not isinstance(media_items, list):
        raise InstagramAPIError("Instagram response did not contain media data.")

    return media_items


def _save_media_item(item: dict) -> bool:
    timestamp = parse_datetime(item.get("timestamp", ""))
    required_fields = ("id", "media_type", "permalink")
    if not all(item.get(field) for field in required_fields) or timestamp is None:
        raise InstagramAPIError("Instagram returned an incomplete media item.")

    media_url = item.get("media_url") or item.get("thumbnail_url")
    if not media_url:
        return False

    InstagramPost.objects.update_or_create(
        insta_id=item["id"],
        defaults={
            "caption": item.get("caption"),
            "media_type": item["media_type"],
            "media_url": media_url,
            "thumbnail_url": item.get("thumbnail_url"),
            "permalink": item["permalink"],
            "timestamp": timestamp,
        },
    )
    return True


def fetch_instagram_posts(limit: int = 12) -> int:
    token, account_id, api_version = _get_api_configuration()
    media_items = _fetch_media_items(token, account_id, api_version, limit)

    saved = 0
    for item in media_items:
        if _save_media_item(item):
            saved += 1

    return saved
