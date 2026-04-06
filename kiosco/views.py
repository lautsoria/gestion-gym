from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from .models import Producto, Venta, DetalleVenta
from django.http import JsonResponse
from django.db import transaction # <--- IMPORTANTE PARA LA SEGURIDAD
import json

@staff_member_required
def terminal_ventas(request):
    productos = Producto.objects.filter(stock__gt=0)
    return render(request, 'kiosco/terminal.html', {'productos': productos})

@staff_member_required
def procesar_venta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            carrito = data.get('carrito', [])
            metodo_pago = data.get('metodo', 'EFECTIVO')
            
            if not carrito:
                return JsonResponse({'status': 'error', 'message': 'Carrito vacío'}, status=400)

            # Usamos transaction.atomic() para que si algo falla, no se guarde a medias
            with transaction.atomic():
                total_venta = 0
                detalles_a_crear = []
                productos_a_actualizar = []

                # 1. Validamos todo y calculamos el total con el precio de la DB (NO el del cliente)
                for item in carrito:
                    cantidad = int(item.get('cantidad', 0))
                    if cantidad <= 0:
                        raise ValueError("No se permiten cantidades negativas o nulas.")

                    # Buscamos el producto en la DB Y LO BLOQUEAMOS temporalmente
                    producto = Producto.objects.select_for_update().get(id=item['id'])
                    
                    if producto.stock < cantidad:
                        raise ValueError(f"No hay stock suficiente de {producto.nombre}.")

                    # Calculamos con el precio REAL
                    subtotal = producto.precio * cantidad
                    total_venta += subtotal

                    # Guardamos temporalmente en listas
                    detalles_a_crear.append({
                        'producto': producto,
                        'cantidad': cantidad,
                        'precio_unitario': producto.precio
                    })
                    
                    # Restamos stock
                    producto.stock -= cantidad
                    productos_a_actualizar.append(producto)

                # 2. Si todo es válido, guardamos la Venta en la DB
                nueva_venta = Venta.objects.create(
                    total=total_venta,
                    vendedor=request.user,
                    metodo=metodo_pago
                )

                # 3. Creamos los detalles
                for d in detalles_a_crear:
                    DetalleVenta.objects.create(
                        venta=nueva_venta,
                        producto=d['producto'],
                        cantidad=d['cantidad'],
                        precio_unitario=d['precio_unitario']
                    )

                # 4. Actualizamos el stock de los productos
                Producto.objects.bulk_update(productos_a_actualizar, ['stock'])

            return JsonResponse({'status': 'ok'})

        except Producto.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Un producto del carrito ya no existe.'}, status=404)
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Error inesperado al procesar la venta.'}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)