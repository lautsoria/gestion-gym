from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone


class Clase(models.Model):
    nombre_actividad = models.CharField(max_length=100)
    instructor = models.CharField(max_length=100)
    horario = models.DateTimeField()
    capacidad_maxima = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre_actividad} - {self.horario.strftime('%d/%m %H:%M')}"


class Pago(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE) 
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.usuario.username} - ${self.monto}"


class Inscripcion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE)
    fecha_reserva = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'clase')

    def __str__(self):
        return f"{self.usuario.username} en {self.clase.nombre_actividad}"
    
class Pago(models.Model):
    # Definimos las opciones
    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('TARJETA', 'Tarjeta'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateField(default=timezone.now)
    # Nueva columna con opciones
    metodo = models.CharField(
        max_length=20, 
        choices=METODOS_PAGO, 
        default='EFECTIVO'
    )

    def __str__(self):
        return f"{self.usuario.username} - ${self.monto} ({self.get_metodo_display()})"