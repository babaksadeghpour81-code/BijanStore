from django.urls import path
from . import views, product_views

app_name = 'vendors'

urlpatterns = [
    # داشبورد
    path('dashboard/', views.dashboard, name='dashboard'),

    # سفارش‌ها
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),

    # محصولات
    path('products/', product_views.product_list, name='product_list'),
    path('products/create/', product_views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', product_views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', product_views.product_delete, name='product_delete'),
    path('products/<int:pk>/images/', product_views.product_images, name='product_images'),
    path('products/<int:pk>/images/<int:image_id>/set-main/', product_views.image_set_main, name='image_set_main'),
    path('products/<int:pk>/images/<int:image_id>/delete/', product_views.image_delete, name='image_delete'),
    path('settlements/', views.settlements_list, name='settlements_list'),
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.coupon_create, name='coupon_create'),
    path('coupons/<int:coupon_id>/toggle/', views.coupon_toggle, name='coupon_toggle'),
]