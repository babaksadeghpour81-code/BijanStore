from django.urls import path
from . import views, payment_views

app_name = 'orders'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('remove/<int:item_id>/', views.cart_remove, name='cart_remove'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/review/', views.checkout_review, name='checkout_review'),
    path('checkout/place-order/', views.place_order, name='place_order'),
    path('success/', views.order_success, name='order_success'),

    # سفارش‌ها
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    path('payment/start/<str:order_number>/', payment_views.payment_start, name='payment_start'),
    path('payment/callback/<str:order_number>/', payment_views.payment_callback, name='payment_callback'),
    path('checkout/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('checkout/remove-coupon/<int:vendor_id>/', views.remove_coupon, name='remove_coupon'),
    path('order/<str:order_number>/delete/', views.order_delete, name='order_delete'),
]