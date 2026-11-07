from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('vendors/', views.vendor_management, name='vendor_management'),
    path('vendors/<int:vendor_id>/approve/', views.vendor_approve, name='vendor_approve'),
    path('settlements/', views.settlements, name='settlements'),
    path('settlements/create/<int:vendor_id>/', views.settlement_create, name='settlement_create'),
    path('settlements/<int:settlement_id>/mark-paid/', views.settlement_mark_paid, name='settlement_mark_paid'),
    path('settlements/<int:settlement_id>/cancel/', views.settlement_cancel, name='settlement_cancel'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:category_id>/delete/', views.category_delete, name='category_delete'),
]