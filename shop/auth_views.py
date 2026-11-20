from functools import wraps
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from .forms import ProductManageForm, StudentRegistrationForm
from .models import Product


def owner_required(view_func):
  """Allows only authenticated staff/shop-owner users; raises 403 otherwise."""

  @login_required
  @wraps(view_func)
  def _wrapped_view(request, *args, **kwargs):
    if not request.user.is_staff:
      raise PermissionDenied('Only the shop owner can access this page.')
    return view_func(request, *args, **kwargs)

  return _wrapped_view


def register_view(request):
  if request.user.is_authenticated:
    return redirect('shop:home')

  if request.method == 'POST':
    form = StudentRegistrationForm(request.POST)
    if form.is_valid():
      user = form.save()
      login(request, user)
      return redirect('shop:home')
  else:
    form = StudentRegistrationForm()

  return render(request, 'shop/register.html', {'form': form})


class StudentLoginView(LoginView):
  template_name = 'shop/login.html'
  redirect_authenticated_user = True


class StudentLogoutView(LogoutView):
  next_page = 'shop:home'


@owner_required
def manage_products(request):
  """Shop-owner dashboard to view products and add new items."""
  products = Product.objects.select_related('category').order_by('-created_at')
  if request.method == 'POST':
    form = ProductManageForm(request.POST, request.FILES)
    if form.is_valid():
      form.save()
      return redirect('shop:manage_products')
  else:
    form = ProductManageForm()

  return render(
      request,
      'shop/manage_products.html',
      {'products': products, 'form': form},
  )


@owner_required
def delete_product(request, pk):
  product = get_object_or_404(Product, pk=pk)
  if request.method == 'POST':
    product.delete()
  return redirect('shop:manage_products')