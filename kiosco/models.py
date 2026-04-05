from django.db import models

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    codigo_barras = models.CharField(max_length=50, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.nombre} (${self.precio})"

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    vendedor = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    def __str__(self):
        return f"Venta {self.id} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"