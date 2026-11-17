from django.shortcuts import get_object_or_404, render
from .models import Product


def home(request):
  products = Product.objects.all().order_by('-created_at')
  return render(request, 'shop/product_list.html', {'products': products})


def product_detail(request, pk):
  product = get_object_or_404(Product, pk=pk)
  return render(request, 'shop/product_detail.html', {'product': product})