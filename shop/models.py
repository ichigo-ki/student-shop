from django.contrib.auth.models import User
from django.db import models


class Product(models.Model):
  seller = models.ForeignKey(
      User, on_delete=models.CASCADE, related_name='products'
  )
  title = models.CharField(max_length=200)
  description = models.TextField()
  price = models.DecimalField(max_digits=10, decimal_places=2)
  image = models.ImageField(upload_to='products/', blank=True, null=True)
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return self.title


class Order(models.Model):
  buyer = models.ForeignKey(
      User, on_delete=models.CASCADE, related_name='orders'
  )
  created_at = models.DateTimeField(auto_now_add=True)
  is_completed = models.BooleanField(default=False)

  def __str__(self):
    return f'Order #{self.id} — {self.buyer.username}'

  @property
  def get_cart_total(self):
    return sum(item.get_total for item in self.orderitem_set.all())

  @property
  def get_cart_items_count(self):
    return sum(item.quantity for item in self.orderitem_set.all())


class OrderItem(models.Model):
  order = models.ForeignKey(Order, on_delete=models.CASCADE)
  product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
  quantity = models.PositiveIntegerField(default=1)

  def __str__(self):
    product_name = self.product.title if self.product else 'Deleted Product'
    return f'{self.quantity}x {product_name} (Order #{self.order.id})'

  @property
  def get_total(self):
    if self.product:
      return self.product.price * self.quantity
    return 0