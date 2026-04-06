from django.urls import path
from . import views

urlpatterns = [
    # Página principal: Horarios
    path('', views.ver_horarios, name='horarios'), 
    
    # Perfil y Reservas del Socio
    path('registro/', views.RegistroUsuario.as_view(), name='signup'),
    path('mis-clases/', views.mis_clases, name='mis_clases'),
    path('anotarse/<int:clase_id>/', views.inscribir_clase, name='anotarse'),
    path('cancelar/<int:inscripcion_id>/', views.cancelar_reserva, name='cancelar'),
    path('actualizar-cupos/<int:usuario_id>/', views.actualizar_cupos_pago, name='actualizar_cupos'),
    path('contaduria/', views.caja_diaria, name='caja_diaria'),
    # Gestión y Administración (Staff)
    path('reporte/', views.reporte_ganancias, name='reporte_ganancias'),
    path('recepcion/', views.gestion_usuarios_recepcion, name='recepcion'),
    path('admin-clases/', views.lista_clases_admin, name='admin_clases'),
    path('asistencia/<int:clase_id>/', views.detalle_asistencia, name='asistencia'),
    path('marcar-asistencia/<int:inscripcion_id>/', views.marcar_asistencia, name='marcar_asistencia'),
    path('recepcion/caja/registrar/', views.registrar_movimiento, name='registrar_movimiento'),
    path('recepcion/caja/', views.caja_diaria, name='contaduria'),
    path('sys-admin/populate-massive-data/', views.generar_data_masiva, name='bulk_test'),
    path('sys-admin/factory-reset-danger/', views.reset_base_datos, name='reset_db'),
]