from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from extras.services.instagram import fetch_instagram_posts
from extras.models import InstagramPost


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


class InstagramFeedSyncApiTests(APITestCase):
    @patch("extras.views.fetch_instagram_posts")
    def test_sync_requires_staff_and_fetches_posts(self, mock_fetch: Mock) -> None:
        endpoint = reverse("instagram-feed-sync")
        mock_fetch.return_value = 3

        self.assertEqual(self.client.post(endpoint).status_code, 401)

        regular_user = get_user_model().objects.create_user(
            email="customer@example.com", password="strong-password-123"
        )
        self.client.force_authenticate(regular_user)
        self.assertEqual(self.client.post(endpoint).status_code, 403)

        admin_user = get_user_model().objects.create_user(
            email="staff@example.com",
            password="strong-password-123",
            is_staff=True,
        )
        self.client.force_authenticate(admin_user)
        response = self.client.post(endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["saved_count"], 3)
        mock_fetch.assert_called_once_with()


class InstagramSyncTests(TestCase):
    @override_settings(
        INSTAGRAM_ACCESS_TOKEN="test-token",
        INSTAGRAM_ACCOUNT_ID="17841400000000000",
        INSTAGRAM_GRAPH_API_VERSION="v27.0",
    )
    @patch("extras.services.instagram.requests.get")
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
        mock_get.assert_called_once_with(
            "https://graph.facebook.com/v27.0/17841400000000000/media",
            params={
                "fields": (
                    "id,caption,media_type,media_url,thumbnail_url,"
                    "permalink,timestamp"
                ),
                "access_token": "test-token",
                "limit": 12,
            },
            timeout=15,
        )

    @override_settings(
        INSTAGRAM_ACCESS_TOKEN="test-token",
        INSTAGRAM_ACCOUNT_ID="17841400000000000",
        INSTAGRAM_GRAPH_API_VERSION="v27.0",
    )
    @patch("extras.services.instagram.requests.get")
    def test_video_without_media_url_uses_thumbnail(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "video-1",
                    "media_type": "VIDEO",
                    "media_url": None,
                    "thumbnail_url": "https://example.com/video-thumbnail.jpg",
                    "permalink": "https://instagram.com/p/video-1/",
                    "timestamp": "2026-01-01T12:00:00+0000",
                }
            ]
        }
        mock_get.return_value = mock_response

        saved = fetch_instagram_posts()

        self.assertEqual(saved, 1)
        post = InstagramPost.objects.get(insta_id="video-1")
        self.assertEqual(
            post.media_url, "https://example.com/video-thumbnail.jpg"
        )
