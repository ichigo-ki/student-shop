from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Category, Order, OrderItem, Product


class ModelRelationshipTests(TestCase):

  def setUp(self):
    self.snacks = Category.objects.create(name='Snacks', slug='snacks')
    self.drinks = Category.objects.create(name='Drinks', slug='drinks')
    self.lays = Product.objects.create(
        category=self.snacks,
        title="Lay's Crab Chips",
        description='Crispy crab flavored chips',
        price=Decimal('120.00'),
    )
    self.cola = Product.objects.create(
        category=self.drinks,
        title='Coca-Cola 0.5L',
        description='Chilled soda',
        price=Decimal('85.00'),
    )
    self.student = User.objects.create_user(
        username='student1',
        email='student1@ucentralasia.org',
        password='StrongPassword123!',
    )

  def test_category_products_reverse_relation(self):
    self.assertEqual(self.snacks.products.count(), 1)
    self.assertIn(self.lays, self.snacks.products.all())
    self.assertNotIn(self.cola, self.snacks.products.all())

  def test_order_totals_and_item_counts(self):
    order = Order.objects.create(buyer=self.student)
    OrderItem.objects.create(order=order, product=self.lays, quantity=2)
    OrderItem.objects.create(order=order, product=self.cola, quantity=3)

    self.assertEqual(order.get_cart_items_count, 5)
    self.assertEqual(order.get_cart_total, Decimal('495.00'))

  def test_order_item_handles_deleted_product(self):
    order = Order.objects.create(buyer=self.student)
    item = OrderItem.objects.create(order=order, product=self.lays, quantity=2)
    self.lays.delete()
    item.refresh_from_db()

    self.assertIsNone(item.product)
    self.assertEqual(item.get_total, 0)
    self.assertIn('Deleted Product', str(item))


class CatalogAndSearchTests(TestCase):

  def setUp(self):
    self.snacks = Category.objects.create(name='Snacks', slug='snacks')
    self.drinks = Category.objects.create(name='Drinks', slug='drinks')
    self.buldak = Product.objects.create(
        category=self.snacks,
        title='Buldak Hot Chicken Ramen',
        price=Decimal('180.00'),
    )
    self.energy = Product.objects.create(
        category=self.drinks,
        title='Flash Up Energy',
        price=Decimal('95.00'),
    )

  def test_home_view_lists_all_products(self):
    response = self.client.get(reverse('shop:home'))
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'Buldak Hot Chicken Ramen')
    self.assertContains(response, 'Flash Up Energy')

  def test_category_slug_filtering(self):
    response = self.client.get(
        reverse('shop:product_list_by_category', args=['drinks'])
    )
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'Flash Up Energy')
    self.assertNotContains(response, 'Buldak Hot Chicken Ramen')

  def test_search_query_filtering(self):
    response = self.client.get(reverse('shop:home'), {'q': 'Buldak'})
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'Buldak Hot Chicken Ramen')
    self.assertNotContains(response, 'Flash Up Energy')


class AuthAndAccessControlTests(TestCase):

  def setUp(self):
    self.category = Category.objects.create(name='Snacks', slug='snacks')
    self.product = Product.objects.create(
        category=self.category,
        title='Snickers Bar',
        price=Decimal('75.00'),
    )
    self.student = User.objects.create_user(
        username='regular_student',
        email='reg@ucentralasia.org',
        password='StrongPassword123!',
        is_staff=False,
    )
    self.owner = User.objects.create_user(
        username='shop_owner',
        email='owner@ucentralasia.org',
        password='OwnerPassword123!',
        is_staff=True,
    )

  def test_student_registration_creates_non_staff_user(self):
    response = self.client.post(
        reverse('shop:register'),
        {
            'username': 'new_student',
            'email': 'new@ucentralasia.org',
            'first_name': 'Aibek',
            'last_name': 'Kadyrov',
            'password1': 'CampusPass2026!',
            'password2': 'CampusPass2026!',
        },
    )
    self.assertRedirects(response, reverse('shop:home'))
    created_user = User.objects.get(username='new_student')
    self.assertFalse(created_user.is_staff)
    self.assertTrue(created_user.is_authenticated)

  def test_anonymous_user_redirected_from_protected_routes(self):
    protected_urls = [
        reverse('shop:cart_detail'),
        reverse('shop:add_to_cart', args=[self.product.pk]),
        reverse('shop:checkout'),
        reverse('shop:manage_products'),
    ]
    for url in protected_urls:
      response = self.client.get(url)
      self.assertEqual(response.status_code, 302)
      self.assertIn(reverse('shop:login'), response.url)

  def test_regular_student_forbidden_from_owner_management(self):
    self.client.login(
        username='regular_student', password='StrongPassword123!'
    )
    response = self.client.get(reverse('shop:manage_products'))
    self.assertEqual(response.status_code, 403)

    delete_response = self.client.post(
        reverse('shop:delete_product', args=[self.product.pk])
    )
    self.assertEqual(delete_response.status_code, 403)
    self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

  def test_staff_owner_can_access_management_and_create_product(self):
    self.client.login(username='shop_owner', password='OwnerPassword123!')
    get_response = self.client.get(reverse('shop:manage_products'))
    self.assertEqual(get_response.status_code, 200)

    post_response = self.client.post(
        reverse('shop:manage_products'),
        {
            'category': self.category.id,
            'title': 'Nitro Energy 0.5L',
            'description': 'Campus favorite',
            'price': '110.00',
        },
    )
    self.assertRedirects(post_response, reverse('shop:manage_products'))
    self.assertTrue(Product.objects.filter(title='Nitro Energy 0.5L').exists())


class CartAndBusinessRuleTests(TestCase):

  def setUp(self):
    self.category = Category.objects.create(name='Noodles', slug='noodles')
    self.buldak = Product.objects.create(
        category=self.category,
        title='Buldak 2x Spicy',
        price=Decimal('200.00'),
    )
    self.student = User.objects.create_user(
        username='buyer1',
        password='StrongPassword123!',
    )
    self.client.login(username='buyer1', password='StrongPassword123!')

  def test_add_and_remove_cart_items(self):
    self.client.post(reverse('shop:add_to_cart', args=[self.buldak.pk]))
    self.client.post(reverse('shop:add_to_cart', args=[self.buldak.pk]))

    order = Order.objects.get(buyer=self.student, is_completed=False)
    self.assertEqual(order.get_cart_items_count, 2)
    self.assertEqual(order.get_cart_total, Decimal('400.00'))

    item = order.orderitem_set.first()
    self.client.post(reverse('shop:remove_from_cart', args=[item.id]))
    self.assertEqual(order.orderitem_set.count(), 0)

  def test_empty_cart_checkout_does_not_complete_order(self):
    response = self.client.post(reverse('shop:checkout'))
    self.assertRedirects(response, reverse('shop:cart_detail'))
    self.assertFalse(
        Order.objects.filter(buyer=self.student, is_completed=True).exists()
    )

  def test_checkout_completes_non_empty_cart(self):
    # 4 x 200 som = 800 som subtotal
    for _ in range(4):
      self.client.post(reverse('shop:add_to_cart', args=[self.buldak.pk]))

    order = Order.objects.get(buyer=self.student, is_completed=False)
    self.assertEqual(order.get_cart_total, Decimal('800.00'))

    response = self.client.post(reverse('shop:checkout'))
    self.assertEqual(response.status_code, 200)
    order.refresh_from_db()
    self.assertTrue(order.is_completed)