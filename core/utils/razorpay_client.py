import os

import razorpay
from django.conf import settings
from dotenv import load_dotenv
from razorpay import Client

load_dotenv()  # Load environment variables from .env file

client: Client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

client.enable_retry(True)
