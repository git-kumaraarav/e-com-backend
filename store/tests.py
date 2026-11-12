from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import CartItem, Product, SizeVariant, WishList

User = get_user_model()


class StoreApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email='customer@example.com',
            name='Customer',
            password='strong-pass-123',
        )
        self.product = Product.objects.create(
            name='Black dress',
            slug='black-dress',
        )
        self.size_variant = SizeVariant.objects.create(
            size='M',
            price=Decimal('49.99'),
            stock=3,
        )
        self.product.size_variants.add(self.size_variant)

    def authenticate(self) -> None:
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'customer@example.com', 'password': 'strong-pass-123'},
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_products_are_publicly_readable(self) -> None:
        response = self.client.get(reverse('product-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['slug'], 'black-dress')

    def test_customer_can_add_product_to_cart(self) -> None:
        self.authenticate()
        response = self.client.post(
            reverse('cart-item-list'),
            {'product': self.product.pk, 'quantity': 2},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['product'], self.product.pk)
        self.assertEqual(response.data['quantity'], 2)
        self.assertTrue(CartItem.objects.filter(user=self.user, product=self.product).exists())

    def test_customer_can_list_wish_list(self) -> None:
        self.authenticate()
        WishList.objects.create(user=self.user, product=self.product)

        response = self.client.get(reverse('wish-list-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['product'], self.product.pk)

    def test_customer_cannot_manage_products(self) -> None:
        self.authenticate()
        response = self.client.post(
            reverse('product-list'),
            {'name': 'New', 'description': 'A new product'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_register_endpoint_creates_user(self) -> None:
        response = self.client.post(
            reverse('register'),
            {
                'name': 'New User',
                'email': 'new@example.com',
                'password': 'strong-pass-123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())
