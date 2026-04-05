from django.urls import path
from . import views

urlpatterns = [
    path('', views.terminal_ventas, name='kiosco'),
    path('procesar/', views.procesar_venta, name='procesar_venta'),
]