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
            'stock': '15',
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
    self.assertEqual(order.get_cart_total, Decimal('760.00'))

    response = self.client.post(reverse('shop:checkout'))
    self.assertEqual(response.status_code, 200)
    order.refresh_from_db()
    self.assertTrue(order.is_completed)


class OOPAndStockTests(TestCase):
  def setUp(self):
    self.category = Category.objects.create(name='Snacks', slug='snacks')
    self.item = Product.objects.create(
      category=self.category,
           title='Campus Snack Pack',
           price=Decimal('200.00'),
           stock=5,
    )
    self.out_of_stock_item = Product.objects.create(
           category=self.category,
           title='Sold Out Soda',
           price=Decimal('90.00'),
           stock=0,
    )
    self.student = User.objects.create_user(
           username='oop_student',
           password='StrongPassword123!',
    )
    self.client.login(username='oop_student', password='StrongPassword123!')

  def test_below_800_som_uses_standard_pricing(self):
    for _ in range(3):  # 3 x 200 = 600 KGS (< 800 KGS)
      self.client.post(reverse('shop:add_to_cart', args=[self.item.pk]))

    order = Order.objects.get(buyer=self.student, is_completed=False)
    self.assertEqual(order.get_subtotal, Decimal('600.00'))
    self.assertEqual(order.get_discount_amount, Decimal('0.00'))
    self.assertEqual(order.get_cart_total, Decimal('600.00'))

  def test_bulk_discount_and_stock_deduction_at_800_som(self):
    for _ in range(4):  # 4 x 200 = 800 KGS (>= 800 KGS -> 5% off = 760 KGS)
      response = self.client.post(
          reverse('shop:add_to_cart', args=[self.item.pk])
      )
      self.assertEqual(response.status_code, 302)

    order = Order.objects.get(buyer=self.student, is_completed=False)
    self.assertEqual(order.get_subtotal, Decimal('800.00'))
    self.assertEqual(order.get_discount_amount, Decimal('40.00'))
    self.assertEqual(order.get_cart_total, Decimal('760.00'))

    checkout_response = self.client.post(reverse('shop:checkout'))
    self.assertEqual(checkout_response.status_code, 200)

    order.refresh_from_db()
    self.item.refresh_from_db()
    self.assertTrue(order.is_completed)
    self.assertEqual(self.item.stock, 1)  # 5 initial - 4 bought = 1 left

  def test_cannot_add_more_than_available_stock(self):
    for _ in range(6):  # stock is only 5
      self.client.post(reverse('shop:add_to_cart', args=[self.item.pk]))

    order = Order.objects.get(buyer=self.student, is_completed=False)
    self.assertEqual(order.get_cart_items_count, 5)

  def test_cannot_add_out_of_stock_product(self):
    self.client.post(
        reverse('shop:add_to_cart', args=[self.out_of_stock_item.pk])
    )
    self.assertFalse(
        Order.objects.filter(buyer=self.student, is_completed=False).exists()
    )

class OrderHistoryTests(TestCase):

  def setUp(self):
    self.category = Category.objects.create(name='Drinks', slug='drinks')
    self.coffee = Product.objects.create(
        category=self.category,
        title='Iced Latte',
        price=Decimal('250.00'),
        stock=10,
    )
    self.student = User.objects.create_user(
        username='history_student',
        password='StrongPassword123!',
    )
    self.other_student = User.objects.create_user(
        username='other_student',
        password='StrongPassword123!',
    )

  def test_anonymous_user_redirected_from_order_history(self):
    response = self.client.get(reverse('shop:order_history'))
    self.assertEqual(response.status_code, 302)
    self.assertIn(reverse('shop:login'), response.url)

  def test_order_history_shows_only_own_completed_orders(self):
    # Completed order for student (4 x 250 = 1000 KGS -> 5% discount = 950 KGS)
    completed_order = Order.objects.create(
        buyer=self.student, is_completed=True
    )
    OrderItem.objects.create(
        order=completed_order, product=self.coffee, quantity=4
    )

    # Active (incomplete) cart for student — should NOT appear in order history
    active_cart = Order.objects.create(buyer=self.student, is_completed=False)
    OrderItem.objects.create(order=active_cart, product=self.coffee, quantity=1)

    # Completed order for another user — should NOT appear
    other_order = Order.objects.create(
        buyer=self.other_student, is_completed=True
    )
    OrderItem.objects.create(order=other_order, product=self.coffee, quantity=2)

    self.client.login(username='history_student', password='StrongPassword123!')
    response = self.client.get(reverse('shop:order_history'))

    self.assertEqual(response.status_code, 200)
    self.assertEqual(list(response.context['orders']), [completed_order])
    self.assertContains(response, f'Order #{completed_order.id}')
    self.assertContains(response, '950.00 KGS')
    self.assertNotContains(response, f'Order #{active_cart.id}')
    self.assertNotContains(response, f'Order #{other_order.id}')