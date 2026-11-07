from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/read/', views.mark_read, name='mark_read'),
    path('<int:notification_id>/click/', views.notification_click, name='click'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
]