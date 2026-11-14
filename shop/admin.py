from django.contrib import admin
from .models import Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
  list_display = ('title', 'seller', 'price', 'created_at')
  list_filter = ('created_at',)
  search_fields = ('title', 'description')


class OrderItemInline(admin.TabularInline):
  model = OrderItem
  extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
  list_display = ('id', 'buyer', 'is_completed', 'created_at')
  list_filter = ('is_completed', 'created_at')
  inlines = [OrderItemInline]