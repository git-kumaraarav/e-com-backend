from celery import shared_task

from core.utils.email_utils import send_otp_email
from extras.services.instagram import fetch_instagram_posts


@shared_task
def send_otp_email_task(
    to_email: str, otp_code: str, recipient_name: str = ""
) -> str:
    return send_otp_email(to_email, otp_code, recipient_name)

@shared_task(name="core.tasks.sync_instagram_feed_task")
def sync_instagram_feed_task() -> None:
    fetch_instagram_posts()
