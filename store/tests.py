from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from users.models import Address

from .models import Cart, CartItem, Order, Product, SizeVariant, WishList

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
            product=self.product,
            size='M',
            price=Decimal('49.99'),
            stock=3,
        )

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
            {'add_item': self.size_variant.pk, 'quantity': 2},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertTrue(
            CartItem.objects.filter(
                cart__user=self.user,
                variant=self.size_variant,
                quantity=2,
            ).exists()
        )

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

    def test_catalog_discovery_endpoints_include_hyperlinked_products(self) -> None:
        search_response = self.client.get(reverse('search-list'), {'q': 'dress'})
        newly_launched_response = self.client.get(reverse('newly-launched-list'))

        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(newly_launched_response.status_code, 200)

    def test_customer_can_checkout_their_cart(self) -> None:
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.size_variant, quantity=2)
        address = Address.objects.create(
            user=self.user,
            name='Home',
            street='123 Main Street',
            city='Springfield',
            state='State',
            postal_code='12345',
            country='Country',
        )
        self.authenticate()

        response = self.client.post(
            reverse('checkout'),
            {'address': address.pk},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.shipping_address, address.get_full_address)
        self.assertEqual(order.items.get().unit_price, Decimal('49.99'))
        self.size_variant.refresh_from_db()
        self.assertEqual(self.size_variant.stock, 1)
        self.assertFalse(CartItem.objects.filter(cart=cart).exists())

    def test_customer_cannot_checkout_with_another_users_address(self) -> None:
        other_user = User.objects.create_user(
            email='other@example.com',
            name='Other Customer',
            password='strong-pass-123',
        )
        address = Address.objects.create(
            user=other_user,
            name='Home',
            street='123 Main Street',
            city='Springfield',
            state='State',
            postal_code='12345',
            country='Country',
        )
        self.authenticate()

        response = self.client.post(
            reverse('checkout'),
            {'address': address.pk},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.filter(user=self.user).exists())
