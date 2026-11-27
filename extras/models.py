from django.db import models


class InstagramPost(models.Model):
    insta_id = models.CharField(max_length=255, unique=True)
    caption = models.TextField(blank=True, null=True)
    media_type = models.CharField(max_length=50)
    media_url = models.URLField(max_length=1000)
    thumbnail_url = models.URLField(max_length=1000, blank=True, null=True)
    permalink = models.URLField(max_length=1000)
    timestamp = models.DateTimeField()

    def __str__(self) -> str:
        return f"Instagram post {self.insta_id}"
