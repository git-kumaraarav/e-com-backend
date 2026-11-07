from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from .instagram import fetch_instagram_posts
from .models import InstagramPost


class InstagramFeedApiTests(APITestCase):
    def test_feed_is_public_and_limited_to_nine_posts(self) -> None:
        for index in range(10):
            InstagramPost.objects.create(
                insta_id=str(index),
                media_type="IMAGE",
                media_url=f"https://example.com/{index}.jpg",
                permalink=f"https://instagram.com/p/{index}/",
                timestamp=f"2026-01-{index + 1:02d}T00:00:00Z",
            )

        response = self.client.get(reverse("instagram-feed-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 9)
        self.assertEqual(response.data[0]["insta_id"], "9")


class InstagramSyncTests(TestCase):
    @override_settings(INSTA_LONG_LIVED_TOKEN="test-token")
    @patch("store.instagram.requests.get")
    def test_sync_creates_and_updates_posts(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "post-1",
                    "caption": "Updated caption",
                    "media_type": "IMAGE",
                    "media_url": "https://example.com/image.jpg",
                    "permalink": "https://instagram.com/p/post-1/",
                    "timestamp": "2026-01-01T12:00:00+0000",
                }
            ]
        }
        mock_get.return_value = mock_response

        saved = fetch_instagram_posts()

        self.assertEqual(saved, 1)
        self.assertEqual(
            InstagramPost.objects.get(insta_id="post-1").caption,
            "Updated caption",
        )
        mock_get.assert_called_once()
