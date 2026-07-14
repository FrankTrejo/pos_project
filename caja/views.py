from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Sum
from django.core.paginator import Paginator
from django.contrib import messages
from decimal import Decimal

from .models import CuadreCaja
from tables.models import Venta, Pago, TasaBCV

@staff_member_required
def cuadre_caja_list(request):
    cuadres = CuadreCaja.objects.all().order_by('-fecha_hora')
    paginator = Paginator(cuadres, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'caja/cuadre_caja_list.html', {'cuadres': page_obj})

@staff_member_required
def cuadre_caja_nuevo(request):
    from django.utils.dateparse import parse_date
    
    hoy = timezone.localtime().date()
    fecha_str = request.GET.get('fecha', hoy.strftime('%Y-%m-%d'))
    fecha_obj = parse_date(fecha_str) if fecha_str else hoy

    # 1. Obtener ventas y pagos válidos de esa fecha
    ventas_validas = Venta.objects.filter(fecha__date=fecha_obj, anulada=False)
    pagos = Pago.objects.filter(venta__in=ventas_validas)

    # 2. Calcular el TOTAL de ventas del día
    total_ventas_dia = ventas_validas.aggregate(Sum('total'))['total__sum'] or Decimal('0.0')

    if request.method == 'POST':
        # Recuperar todos los montos del formulario
        fondo_caja = Decimal(request.POST.get('fondo_caja_usd', '0').replace(',', '.'))
        gastos_turno = Decimal(request.POST.get('gastos_turno_usd', '0').replace(',', '.'))
        rec_efectivo_usd = Decimal(request.POST.get('recibido_efectivo_usd', '0').replace(',', '.'))
        rec_efectivo_bs = Decimal(request.POST.get('recibido_efectivo_bs', '0').replace(',', '.'))
        rec_electronico_usd = Decimal(request.POST.get('recibido_electronico_usd', '0').replace(',', '.'))
        rec_electronico_bs = Decimal(request.POST.get('recibido_electronico_bs', '0').replace(',', '.'))
        notas = request.POST.get('notas', '')

        # Calcular totales en USD
        tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
        tasa = tasa_obj.precio if tasa_obj and tasa_obj.precio > 0 else Decimal('1.0')

        total_recibido = (rec_efectivo_usd + 
                          (rec_efectivo_bs / tasa) + 
                          rec_electronico_usd + 
                          (rec_electronico_bs / tasa))
        
        total_esperado = total_ventas_dia + fondo_caja - gastos_turno
        diferencia = total_recibido - total_esperado

        # Validación: Si hay faltante, la nota es obligatoria
        if diferencia < 0 and not notas.strip():
            messages.error(request, "¡Hay un faltante! Debes dejar una nota explicando el motivo para poder cerrar la caja.")
            # Devolvemos el control al formulario sin guardar, pero manteniendo los datos (esto es más complejo, por ahora solo mostramos error)
            # Para una mejor UX, se necesitaría pasar los datos de vuelta al contexto.
            # Por simplicidad en este paso, solo bloqueamos el guardado.
            return redirect(request.get_full_path())

        CuadreCaja.objects.create(
            fecha_cuadre=fecha_obj,
            usuario=request.user,
            total_ventas_dia=total_ventas_dia,
            fondo_caja_usd=fondo_caja,
            gastos_turno_usd=gastos_turno,
            recibido_efectivo_usd=rec_efectivo_usd,
            recibido_efectivo_bs=rec_efectivo_bs,
            recibido_electronico_usd=rec_electronico_usd,
            recibido_electronico_bs=rec_electronico_bs,
            total_recibido_usd=total_recibido,
            total_esperado_usd=total_esperado,
            diferencia_usd=diferencia,
            notas=notas,
        )
        
        messages.success(request, "¡Cuadre de caja guardado exitosamente!")
        return redirect('cuadre_caja_list')

    context = {
        'fecha_obj': fecha_obj,
        'fecha_str': fecha_str,
        'total_ventas_dia': total_ventas_dia,
        'tasa_bcv': TasaBCV.objects.order_by('-fecha_actualizacion').first().precio or Decimal('1.0')
    }
    return render(request, 'caja/cuadre_caja_form.html', context)
