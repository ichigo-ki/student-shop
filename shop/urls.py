from django.urls import path
from . import auth_views, views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path(
        'category/<slug:category_slug>/',
        views.home,
        name='product_list_by_category',
    ),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path(
        'cart/remove/<int:item_id>/',
        views.remove_from_cart,
        name='remove_from_cart',
    ),
    path('checkout/', views.checkout, name='checkout'),
    # Auth & shop-owner management routes
    path('register/', auth_views.register_view, name='register'),
    path('login/', auth_views.StudentLoginView.as_view(), name='login'),
    path('logout/', auth_views.StudentLogoutView.as_view(), name='logout'),
    path('manage/', auth_views.manage_products, name='manage_products'),
    path(
        'manage/delete/<int:pk>/',
        auth_views.delete_product,
        name='delete_product',
    ),
]