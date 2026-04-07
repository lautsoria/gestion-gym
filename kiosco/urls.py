from django.urls import path
from . import views

urlpatterns = [
    path('', views.terminal_ventas, name='kiosco'),
    path('procesar/', views.procesar_venta, name='procesar_venta'),
    path('nuevo-producto/', views.crear_producto_kiosco, name='crear_producto_kiosco'),
    path('ajustar-stock/<int:producto_id>/', views.ajustar_stock, name='ajustar_stock'),
    path('editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('producto/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
]