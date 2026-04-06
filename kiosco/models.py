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
    METODOS_PAGO = [('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('TARJETA', 'Tarjeta')]
    
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    vendedor = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    # AÑADIMOS ESTO:
    metodo = models.CharField(max_length=20, choices=METODOS_PAGO, default='EFECTIVO')

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        if es_nuevo:
            from gestion_gym.models import MovimientoCaja 
            MovimientoCaja.objects.create(
                tipo='INGRESO',
                monto=self.total,
                concepto=f"Venta Kiosco #{self.id}",
                metodo=self.metodo, # <-- USAMOS EL MÉTODO DE LA VENTA
                usuario_afectado=self.vendedor
            )
    def __str__(self):
        return f"Venta {self.id} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"