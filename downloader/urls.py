from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('setup/', views.create_request, name='create_request'),
    path('payment/<uuid:pk>/', views.payment_page, name='payment_page'),
    path('status/<uuid:pk>/', views.check_status, name='check_status'),
    path('webhook/sepay', views.sepay_webhook, name='sepay_webhook'),
    path('download/<uuid:pk>/', views.download_page, name='download_page'),
]
