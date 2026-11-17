from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Order, OrderItem, Product


def home(request):
  products = Product.objects.all().order_by('-created_at')
  return render(request, 'shop/product_list.html', {'products': products})


def product_detail(request, pk):
  product = get_object_or_404(Product, pk=pk)
  return render(request, 'shop/product_detail.html', {'product': product})


@login_required
def add_to_cart(request, pk):
  product = get_object_or_404(Product, pk=pk)
  order, _ = Order.objects.get_or_create(buyer=request.user, is_completed=False)
  order_item, created = OrderItem.objects.get_or_create(
      order=order, product=product
  )

  if not created:
    order_item.quantity += 1
    order_item.save()

  return redirect('shop:cart_detail')


@login_required
def cart_detail(request):
  order = Order.objects.filter(buyer=request.user, is_completed=False).first()
  return render(request, 'shop/cart.html', {'order': order})


@login_required
def remove_from_cart(request, item_id):
  order_item = get_object_or_404(
      OrderItem, id=item_id, order__buyer=request.user, order__is_completed=False
  )
  order_item.delete()
  return redirect('shop:cart_detail')


@login_required
def checkout(request):
  order = Order.objects.filter(buyer=request.user, is_completed=False).first()
  if order and request.method == 'POST':
    order.is_completed = True
    order.save()
    return render(request, 'shop/checkout_success.html', {'order': order})
  return redirect('shop:cart_detail')