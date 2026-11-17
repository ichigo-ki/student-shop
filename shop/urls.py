from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path(
        'cart/remove/<int:item_id>/',
        views.remove_from_cart,
        name='remove_from_cart',
    ),
    path('checkout/', views.checkout, name='checkout'),
]