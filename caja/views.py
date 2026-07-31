from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.contrib import messages
from decimal import Decimal

from .models import CuadreCaja
from tables.models import Venta, Pago, TasaBCV
from core.models import Configuracion

@staff_member_required
def cuadre_caja_list(request):
    cuadres = CuadreCaja.objects.all().order_by('-fecha_hora')
    paginator = Paginator(cuadres, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'caja/cuadre_caja_list.html', {'cuadres': page_obj})

@staff_member_required
def cuadre_caja_nuevo(request):
    hoy = timezone.localtime().date()
    fecha_str = request.GET.get('fecha', hoy.strftime('%Y-%m-%d'))
    fecha_obj = parse_date(fecha_str) if fecha_str else hoy

    # 1. Tasas de Cambio
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_bcv_real = tasa_obj.precio if tasa_obj and tasa_obj.precio > 0 else Decimal('1.0')
    
    config = Configuracion.objects.first()
    
    # Determinar Tasa General
    tasa_general = Decimal('1.0')
    if config:
        if config.usar_scraping_bcv:
            tasa_general = tasa_bcv_real
        else:
            tasa_general = config.tasa_dolar
    else:
        tasa_general = tasa_bcv_real
    tasa_cashea = Decimal('0.0')
    if config:
        if config.usar_tasa_bcv_para_cashea:
            tasa_cashea = tasa_bcv_real
        elif config.tasa_cashea > 0:
            tasa_cashea = config.tasa_cashea
        else:
            tasa_cashea = tasa_general
    else:
        tasa_cashea = tasa_general

    # 2. Obtener ventas y separar Cashea de General y automatizar totales por método de pago y propinas
    ventas_validas = Venta.objects.filter(fecha__date=fecha_obj, anulada=False)
    
    ventas_sistema_cashea = Decimal('0.0')
    ventas_sistema_general = Decimal('0.0')
    total_propinas_sistema = Decimal('0.0')

    auto_punto_venta_bs = Decimal('0.0')
    auto_efectivo_bs = Decimal('0.0')
    auto_pago_movil_bs = Decimal('0.0')
    auto_dolares_usd = Decimal('0.0')
    auto_cashea_recibido_usd = Decimal('0.0')
    auto_cashea_financiado_usd = Decimal('0.0')

    for v in ventas_validas:
        pagos = v.pagos.all()
        tiene_cashea = any(p.metodo == 'CASHEA' or 'cashea' in str(p.metodo).lower() for p in pagos)
        total_propinas_sistema += Decimal(str(v.propina or 0))
        
        # Tasa a utilizar para convertir los montos en USD de los pagos en BS a Bolívares
        tasa_uso = Decimal(str(v.tasa_aplicada)) if v.tasa_aplicada and Decimal(str(v.tasa_aplicada)) > 0 else tasa_general
        
        total_pagado_cashea_en_venta = Decimal('0.0')

        for p in pagos:
            monto_pago = Decimal(str(p.monto))
            if p.metodo == 'PUNTO':
                auto_punto_venta_bs += monto_pago * tasa_uso
            elif p.metodo == 'EFECTIVO_BS':
                auto_efectivo_bs += monto_pago * tasa_uso
            elif p.metodo == 'PAGO_MOVIL':
                auto_pago_movil_bs += monto_pago * tasa_uso
            elif p.metodo == 'EFECTIVO_USD':
                auto_dolares_usd += monto_pago
            elif p.metodo == 'CASHEA' or 'cashea' in str(p.metodo).lower():
                auto_cashea_recibido_usd += monto_pago
                total_pagado_cashea_en_venta += monto_pago

        if tiene_cashea:
            ventas_sistema_cashea += Decimal(str(v.total))
            pago_inicial_cashea = max(Decimal('0.0'), total_pagado_cashea_en_venta - Decimal(str(v.propina or 0)))
            monto_fin = Decimal(str(v.total)) - pago_inicial_cashea
            if monto_fin > 0:
                auto_cashea_financiado_usd += monto_fin
        else:
            ventas_sistema_general += Decimal(str(v.total))

    total_ventas_sistema = ventas_sistema_cashea + ventas_sistema_general

    if request.method == 'POST':
        # Valores Esperados / Fondo
        fondo_caja_usd = Decimal(request.POST.get('fondo_caja_usd', '0').replace(',', '.'))
        
        # Inputs $
        dolares_usd = Decimal(request.POST.get('dolares_usd', '0').replace(',', '.'))
        cashea_recibido_usd = Decimal(request.POST.get('cashea_recibido_usd', '0').replace(',', '.'))
        cashea_financiado_usd = Decimal(request.POST.get('cashea_financiado_usd', '0').replace(',', '.'))
        gastos_usd = Decimal(request.POST.get('gastos_usd', '0').replace(',', '.'))
        
        # Inputs BS
        punto_venta_bs = Decimal(request.POST.get('punto_venta_bs', '0').replace(',', '.'))
        efectivo_bs = Decimal(request.POST.get('efectivo_bs', '0').replace(',', '.'))
        pago_movil_bs = Decimal(request.POST.get('pago_movil_bs', '0').replace(',', '.'))
        gastos_bs = Decimal(request.POST.get('gastos_bs', '0').replace(',', '.'))
        
        notas = request.POST.get('notas', '')

        # Cálculos de Cuadre
        punto_venta_usd_calc = punto_venta_bs / tasa_general if tasa_general else 0
        efectivo_usd_calc = efectivo_bs / tasa_general if tasa_general else 0
        pago_movil_usd_calc = pago_movil_bs / tasa_general if tasa_general else 0
        gastos_bs_usd_calc = gastos_bs / tasa_general if tasa_general else 0
        
        # TOTAL RECIBIDO: Se suma el físico/banco/cashea recibido + Los Gastos (porque justifican el dinero faltante)
        # Nota: El Cashea Financiado no es dinero físico recibido, no debe sumarse al total recibido.
        total_recibido_usd = (
            punto_venta_usd_calc + 
            efectivo_usd_calc + 
            pago_movil_usd_calc + 
            dolares_usd + 
            cashea_recibido_usd + 
            gastos_usd + 
            gastos_bs_usd_calc
        )
        
        # TOTAL ESPERADO: Lo que el sistema dice que vendiste + las propinas + el fondo con el que empezaste MENOS lo financiado por Cashea
        total_esperado_usd = (total_ventas_sistema + total_propinas_sistema + fondo_caja_usd) - cashea_financiado_usd
        
        # DIFERENCIA
        diferencia = total_recibido_usd - total_esperado_usd

        # Validación
        if diferencia < 0 and not notas.strip():
            messages.error(request, "¡Hay un faltante! Debes dejar una nota explicando el motivo para poder cerrar la caja.")
            return redirect(request.get_full_path())

        CuadreCaja.objects.create(
            fecha_cuadre=fecha_obj,
            usuario=request.user,
            tasa_general=tasa_general,
            tasa_cashea=tasa_cashea,
            ventas_sistema_general=ventas_sistema_general,
            ventas_sistema_cashea=ventas_sistema_cashea,
            total_ventas_sistema=total_ventas_sistema,
            total_propinas_sistema=total_propinas_sistema,
            fondo_caja_usd=fondo_caja_usd,
            dolares_usd=dolares_usd,
            cashea_recibido_usd=cashea_recibido_usd,
            cashea_financiado_usd=cashea_financiado_usd,
            gastos_usd=gastos_usd,
            punto_venta_bs=punto_venta_bs,
            efectivo_bs=efectivo_bs,
            pago_movil_bs=pago_movil_bs,
            gastos_bs=gastos_bs,
            total_recibido_usd=total_recibido_usd,
            total_esperado_usd=total_esperado_usd,
            diferencia_usd=diferencia,
            notas=notas,
        )
        
        messages.success(request, "¡Cuadre de caja guardado exitosamente!")
        return redirect('cuadre_caja_list')

    context = {
        'fecha_obj': fecha_obj,
        'fecha_str': fecha_str,
        'total_ventas_sistema': total_ventas_sistema,
        'total_propinas_sistema': total_propinas_sistema,
        'tasa_general': tasa_general,
        'tasa_cashea': tasa_cashea,
        'auto_punto_venta_bs': f"{auto_punto_venta_bs:.2f}",
        'auto_efectivo_bs': f"{auto_efectivo_bs:.2f}",
        'auto_pago_movil_bs': f"{auto_pago_movil_bs:.2f}",
        'auto_dolares_usd': f"{auto_dolares_usd:.2f}",
        'auto_cashea_recibido_usd': f"{auto_cashea_recibido_usd:.2f}",
        'auto_cashea_financiado_usd': f"{auto_cashea_financiado_usd:.2f}",
    }
    return render(request, 'caja/cuadre_caja_form.html', context)

