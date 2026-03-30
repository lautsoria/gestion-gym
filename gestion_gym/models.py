from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class Clase(models.Model):
    nombre_actividad = models.CharField(max_length=100)
    instructor = models.CharField(max_length=100)
    horario = models.DateTimeField()
    capacidad_maxima = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre_actividad} - {self.horario.strftime('%d/%m %H:%M')}"

class Pago(models.Model):
    METODOS_PAGO = [('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('TARJETA', 'Tarjeta')]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_clases = models.PositiveIntegerField(default=12) 
    fecha_pago = models.DateField(default=timezone.now)
    metodo = models.CharField(max_length=20, choices=METODOS_PAGO, default='EFECTIVO')
    
    def save(self, *args, **kwargs):
        perfil, created = Perfil.objects.get_or_create(usuario=self.usuario)
        perfil.clases_disponibles += self.cantidad_clases
        
        
        perfil.fecha_vencimiento = timezone.now().date() + timezone.timedelta(days=30)
        
        perfil.save()
        super().save(*args, **kwargs)

   

    def __str__(self):
        return f"{self.usuario.username} compró {self.cantidad_clases} clases"

class Inscripcion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE)
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    asistio = models.BooleanField(default=False) 

    class Meta:
        unique_together = ('usuario', 'clase')
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

    def __str__(self):
        estado = "Presente" if self.asistio else "Ausente"
        return f"{self.usuario.username} en {self.clase.nombre_actividad} ({estado})"
    
class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    clases_disponibles = models.IntegerField(default=0)
    fecha_vencimiento = models.DateField(null=True, blank=True) 
    
    def limpiar_vencidos(self):
        """Lógica para resetear cupos si pasó la fecha"""
        if self.fecha_vencimiento and self.fecha_vencimiento < timezone.now().date():
            if self.clases_disponibles > 0:
                self.clases_disponibles = 0
                self.save()
        return self
    
    def __str__(self):
        return f"{self.usuario.username} - Créditos: {self.clases_disponibles} (Vence: {self.fecha_vencimiento})"  


# Estos "signals" crean automáticamente un perfil cuando se registra un usuario nuevo
@receiver(post_save, sender=User)
def crear_perfil(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(usuario=instance)    