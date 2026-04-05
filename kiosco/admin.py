# kiosco/admin.py
from django.contrib import admin
from .models import Producto, Venta, DetalleVenta

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ('producto', 'cantidad', 'precio_unitario')

@admin.register(Producto) # <--- Esto ya registra el modelo
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock')
    search_fields = ('nombre',)

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'vendedor', 'total')
    list_filter = ('fecha', 'vendedor')
    inlines = [DetalleVentaInline]

