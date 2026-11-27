# accounts/brevo_mailer.py
import os
from django.conf import settings

from brevo import Brevo
from brevo.core.api_error import ApiError
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

def send_otp_email(to_email: str, otp_code: str, recipient_name: str = "") -> str:
    client = Brevo(api_key=os.getenv("BREVO_API_KEY"), timeout=15.0)

    sender = SendTransacEmailRequestSender(
        email=settings.BREVO_SENDER_EMAIL,
        name=settings.BREVO_SENDER_NAME,
    )
    recipient = SendTransacEmailRequestToItem(
        email=to_email,
        name=recipient_name or to_email,
    )

    try:
        response = client.transactional_emails.send_transac_email(
            subject="Your verification OTP code",
            text_content=f"Your verification code is {otp_code}. It expires in 5 minutes.",
            html_content=(
                f"<p>Your verification code is <strong>{otp_code}</strong>.</p>"
                f"<p>This code expires in 5 minutes. Do not share it with anyone.</p>"
            ),
            sender=sender,
            to=[recipient],
            request_options={"timeout_in_seconds": 10, "max_retries": 2},
        )
        return response.message_id
    except ApiError as exc:
        raise RuntimeError(f"Brevo API error ({exc.status_code}): {exc.body}") from exc