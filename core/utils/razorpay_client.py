
import razorpay
from django.conf import settings
from razorpay import Client

client: Client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

client.enable_retry(True)
