from celery import shared_task

from .services.instagram import fetch_instagram_posts


@shared_task(name="core.tasks.fetch_instagram_feed_task")
def fetch_instagram_feed_task() -> None:
    fetch_instagram_posts()
