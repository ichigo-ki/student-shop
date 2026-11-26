from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Category, Order, Product
from .services import (
    CartService,
    CheckoutService,
    OrderHistoryService,
    PricingFactory,
    ProductCatalogService,
    ShopRuleError,
)


def home(request, category_slug=None):
  category = None
  categories = Category.objects.all()

  if category_slug:
    category = get_object_or_404(Category, slug=category_slug)

  query = request.GET.get('q', '').strip()
  in_stock_only = request.GET.get('in_stock') == '1'
  sort_by = request.GET.get('sort', 'newest')
  if sort_by not in ProductCatalogService.SORT_OPTIONS:
    sort_by = 'newest'

  catalog_service = ProductCatalogService()
  products = catalog_service.get_products(
      category=category,
      query=query,
      in_stock_only=in_stock_only,
      sort_by=sort_by,
  )

  context = {
      'category': category,
      'categories': categories,
      'products': products,
      'query': query,
      'in_stock_only': in_stock_only,
      'sort_by': sort_by,
  }
  return render(request, 'shop/product_list.html', context)


def product_detail(request, pk):
  product = get_object_or_404(Product, pk=pk)
  return render(request, 'shop/product_detail.html', {'product': product})


@login_required
def add_to_cart(request, pk):
  product = get_object_or_404(Product, pk=pk)
  cart_service = CartService(request.user)
  try:
    cart_service.add_product(product, quantity=1)
    messages.success(request, f'Added "{product.title}" to your cart.')
  except ShopRuleError as exc:
    messages.error(request, str(exc))
  return redirect('shop:cart_detail')


@login_required
def cart_detail(request):
  order = Order.objects.filter(buyer=request.user, is_completed=False).first()
  pricing_strategy = None
  if order:
    pricing_strategy = PricingFactory.get_strategy(order.get_subtotal)

  context = {
      'order': order,
      'pricing_strategy': pricing_strategy,
      'bulk_threshold': PricingFactory.BULK_THRESHOLD,
  }
  return render(request, 'shop/cart.html', context)


@login_required
def remove_from_cart(request, item_id):
  cart_service = CartService(request.user)
  try:
    cart_service.remove_item(item_id)
    messages.info(request, 'Item removed from your cart.')
  except ShopRuleError as exc:
    messages.error(request, str(exc))
  return redirect('shop:cart_detail')


@login_required
def checkout(request):
  if request.method == 'POST':
    checkout_service = CheckoutService(request.user)
    try:
      completed_order = checkout_service.complete_checkout()
      return render(
          request, 'shop/checkout_success.html', {'order': completed_order}
      )
    except ShopRuleError as exc:
      messages.error(request, str(exc))
  return redirect('shop:cart_detail')


@login_required
@require_POST
def update_cart_quantity(request, item_id):
  action = request.POST.get('action')
  delta = (
      1 if action == 'increase' else -1 if action == 'decrease' else 0
  )

  if delta == 0:
    return redirect('shop:view_cart')

  service = CartService(request.user)
  try:
    service.update_quantity(item_id=item_id, delta=delta)
  except ShopRuleError as exc:
    messages.error(request, str(exc))

  return redirect('shop:cart_detail')


@login_required
def order_history(request):
  service = OrderHistoryService(request.user)
  orders = service.get_completed_orders()
  return render(request, 'shop/order_history.html', {'orders': orders})