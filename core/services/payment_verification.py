import razorpay.errors
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from ...store.models import Order
from ...store.serializers import OrderDetailSerializer, PaymentVerificationSerializer
from .razorpay_client import client


def verify_payment(request):
    serializer = PaymentVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # 1. Fetch the order from YOUR database using the razorpay_order_id
    order = get_object_or_404(Order, razorpay_order_id=data["razorpay_order_id"])

    # Prevent duplicate processing if already marked paid
    if order.is_paid:
        return Response(
            {
                "detail": "Order is already verified and paid.",
                "order": OrderDetailSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )

    # 2. Verify the HMAC-SHA256 signature using your DB's razorpay_order_id
    params_dict = {
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_payment_id": data["razorpay_payment_id"],
        "razorpay_signature": data["razorpay_signature"],
    }

    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        return Response(
            {"error": "Payment signature verification failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Signature is valid — mark order as paid and save payment details
    order.razorpay_payment_id = data["razorpay_payment_id"]
    order.razorpay_signature = data["razorpay_signature"]
    order.is_paid = True
    order.save(update_fields=["razorpay_payment_id", "razorpay_signature", "is_paid"])

    return Response(
        {
            "status": "Payment verified successfully",
            "order": OrderDetailSerializer(order).data,
        },
        status=status.HTTP_200_OK,
    )