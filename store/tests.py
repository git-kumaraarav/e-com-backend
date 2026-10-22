from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Order, Product


class StoreApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username='customer', password='strong-pass-123')
        self.product = Product.objects.create(
            name='Black dress',
            slug='black-dress',
            price=Decimal('49.99'),
            stock=3,
        )

    def authenticate(self) -> None:
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'customer', 'password': 'strong-pass-123'},
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_products_are_publicly_readable(self) -> None:
        response = self.client.get(reverse('product-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['slug'], 'black-dress')

    def test_customer_can_create_order_and_stock_is_reserved(self) -> None:
        self.authenticate()
        response = self.client.post(
            reverse('order-list'),
            {
                'shipping_address': '1 Fashion Street',
                'items': [{'product_id': self.product.pk, 'quantity': 2}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['total'], '99.98')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(Order.objects.get().user, self.user)

    def test_customer_cannot_manage_products(self) -> None:
        self.authenticate()
        response = self.client.post(
            reverse('product-list'),
            {'name': 'New', 'slug': 'new', 'price': '10.00', 'stock': 1},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_register_endpoint_creates_user(self) -> None:
        response = self.client.post(
            reverse('register'),
            {'username': 'new-user', 'email': 'new@example.com', 'password': 'strong-pass-123'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username='new-user').exists())
