from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from .models import Order, OrderItem, Product


class ShopRuleError(Exception):
  """Custom domain exception raised when a shop business rule is violated."""


# =========================================================
# 1. ABSTRACTION & POLYMORPHISM: Pricing Strategy Hierarchy
# =========================================================
class PricingStrategy(ABC):
  """Abstract base class defining the contract for order total calculation."""

  @property
  @abstractmethod
  def name(self) -> str:
    """Human-readable label describing the applied pricing rule."""

  @abstractmethod
  def calculate_total(self, subtotal: Decimal) -> Decimal:
    """Return final payable total in KGS after applying strategy rules."""

  def get_discount_amount(self, subtotal: Decimal) -> Decimal:
    """Return the exact KGS discount deducted from the subtotal."""
    subtotal = Decimal(subtotal)
    discount = subtotal - self.calculate_total(subtotal)
    return discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class StandardPricing(PricingStrategy):
  """Default pricing strategy for orders below the bulk discount threshold."""

  @property
  def name(self) -> str:
    return 'Standard Pricing'

  def calculate_total(self, subtotal: Decimal) -> Decimal:
    return Decimal(subtotal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class BulkDiscountPricing(PricingStrategy):
  """Applies a percentage discount when an order reaches the KGS threshold."""

  def __init__(
      self,
      threshold: Decimal = Decimal('800.00'),
      discount_rate: Decimal = Decimal('0.05'),
  ):
    self._threshold = Decimal(threshold)
    self._discount_rate = Decimal(discount_rate)

  @property
  def threshold(self) -> Decimal:
    return self._threshold

  @property
  def discount_rate(self) -> Decimal:
    return self._discount_rate

  @property
  def name(self) -> str:
    percent = int(self._discount_rate * 100)
    return f'Bulk Order Discount ({percent}% off >= {self._threshold} KGS)'

  def calculate_total(self, subtotal: Decimal) -> Decimal:
    subtotal = Decimal(subtotal)
    if subtotal >= self._threshold:
      discounted = subtotal * (Decimal('1.00') - self._discount_rate)
      return discounted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class PricingFactory:
  """Selects the appropriate PricingStrategy polymorphically based on subtotal."""

  BULK_THRESHOLD = Decimal('800.00')
  BULK_RATE = Decimal('0.05')

  @classmethod
  def get_strategy(cls, subtotal: Decimal) -> PricingStrategy:
    if Decimal(subtotal) >= cls.BULK_THRESHOLD:
      return BulkDiscountPricing(
          threshold=cls.BULK_THRESHOLD, discount_rate=cls.BULK_RATE
      )
    return StandardPricing()


# =========================================================
# 2. INHERITANCE & ENCAPSULATION: Cart & Checkout Services
# =========================================================
class BaseShopService(ABC):
  """Base service encapsulating user ownership and active-cart lookup."""

  def __init__(self, user):
    if not user or not user.is_authenticated:
      raise ShopRuleError('You must be logged in to manage a cart.')
    self._user = user

  @property
  def user(self):
    return self._user

  def _get_active_order(self, create: bool = False):
    if create:
      order, _ = Order.objects.get_or_create(
          buyer=self._user, is_completed=False
      )
      return order
    return Order.objects.filter(buyer=self._user, is_completed=False).first()


class CartService(BaseShopService):
  """Encapsulates cart mutations and stock availability validation."""

  def _validate_stock(self, product: Product, desired_qty: int) -> None:
    if product.stock <= 0:
      raise ShopRuleError(f'"{product.title}" is currently out of stock.')
    if desired_qty > product.stock:
      raise ShopRuleError(
          f'Only {product.stock} unit(s) of "{product.title}" left in stock.'
      )

  def add_product(self, product: Product, quantity: int = 1) -> OrderItem:
    if quantity <= 0:
      raise ShopRuleError('Quantity must be at least 1.')

    existing_order = self._get_active_order(create=False)
    existing_item = (
        OrderItem.objects.filter(order=existing_order, product=product).first()
        if existing_order
        else None
    )
    new_qty = (existing_item.quantity if existing_item else 0) + quantity
    self._validate_stock(product, new_qty)

    order = existing_order or self._get_active_order(create=True)
    if existing_item:
      existing_item.quantity = new_qty
      existing_item.save()
      return existing_item

    return OrderItem.objects.create(
        order=order, product=product, quantity=quantity
    )

  def remove_item(self, item_id: int) -> None:
    order = self._get_active_order(create=False)
    if not order:
      raise ShopRuleError('No active cart found.')
    item = OrderItem.objects.filter(id=item_id, order=order).first()
    if not item:
      raise ShopRuleError('Cart item not found.')
    item.delete()


class CheckoutService(BaseShopService):
  """Encapsulates atomic checkout validation, pricing, and stock deduction."""

  @transaction.atomic
  def complete_checkout(self) -> Order:
    order = self._get_active_order(create=False)
    if not order:
      raise ShopRuleError('Your cart is empty.')

    items = list(order.orderitem_set.select_related('product').all())
    if not items:
      raise ShopRuleError('Cannot checkout an empty cart.')

    # Lock product rows during checkout to prevent race-condition overselling
    product_ids = [item.product_id for item in items if item.product_id]
    locked_products = {
        p.id: p
        for p in Product.objects.select_for_update().filter(id__in=product_ids)
    }

    for item in items:
      product = locked_products.get(item.product_id)
      if not product:
        raise ShopRuleError('One of the items in your cart no longer exists.')
      if item.quantity > product.stock:
        raise ShopRuleError(
            f'Insufficient stock for "{product.title}" '
            f'(available: {product.stock}, requested: {item.quantity}).'
        )

    # Deduct stock and finalize order
    for item in items:
      product = locked_products[item.product_id]
      product.stock -= item.quantity
      product.save(update_fields=['stock'])

    order.is_completed = True
    order.save(update_fields=['is_completed'])
    return order