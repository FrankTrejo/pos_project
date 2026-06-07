from core.models import Configuracion
from tables.models import TasaBCV  # <--- IMPORTANTE: Importamos el modelo de la tasa real
import win32print
import threading
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

def to_decimal(valor):
    """ Función auxiliar para convertir cualquier cosa a Decimal de forma segura """
    if valor is None or valor == "":
        return Decimal('0.00')
    try:
        return Decimal(str(valor))
    except (ValueError, InvalidOperation):
        return Decimal('0.00')

def obtener_tasa_real():
    """ 
    Busca la tasa en la tabla TasaBCV. 
    Si no hay ninguna registrada, usa la de Configuracion como respaldo.
    """
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    if tasa_obj:
        return to_decimal(tasa_obj.precio)
    
    # Respaldo si la tabla de tasas está vacía
    config = Configuracion.get_solo()
    return to_decimal(config.tasa_dolar)

def mandar_a_tickera(venta):
    """ Función para la FACTURA FINAL """
    config = Configuracion.get_solo()
    if not config.auto_imprimir or not config.impresora_ticket:
        return False, "Impresora no configurada"

    try:
        # --- CAMBIO CLAVE: Usamos la tasa real del BCV ---
        tasa = obtener_tasa_real()
        
        total_usd = to_decimal(venta.total)
        monto_recibido = to_decimal(venta.monto_recibido)
        propina = to_decimal(venta.propina)
        
        # Cálculo de Bolívares con la tasa de 486.19...
        total_bs = (total_usd * tasa).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        vuelto_usd = monto_recibido - total_usd - propina

        # LOG para que verifiques en la terminal
        print(f"IMPRIMIENDO FACTURA: {venta.codigo_factura}")
        print(f"TASA USADA: {tasa} | TOTAL USD: {total_usd} | TOTAL BS: {total_bs}")

        # Diseño del Ticket
        t = ""
        t += f"{config.nombre_empresa.upper().center(32)}\n"
        t += f"RIF: {config.rif.center(27)}\n"
        t += f"{config.direccion[:32].center(32)}\n"
        if config.telefono: t += f"Telf: {config.telefono.center(26)}\n"
        t += "================================\n"
        t += f"FACTURA: {venta.codigo_factura}\n"
        fecha_local = timezone.localtime(venta.fecha)
        t += f"FECHA: {fecha_local.strftime('%d/%m/%Y %H:%M')}\n"
        t += f"MESA: {venta.mesa_numero} | MESERO: {venta.mesero.username.upper() if venta.mesero else 'CAJA'}\n"
        t += "--------------------------------\n"
        t += "CANT  DESCRIPCION         TOTAL\n"
        t += "--------------------------------\n"

        for item in venta.detalles.all():
            p_base = to_decimal(item.precio_unitario)
            subt_base = p_base * item.cantidad
            
            if getattr(item, 'cuarto_2_producto', None):
                t += f"{item.cantidad}x 4 ESTACIONES   {subt_base:>8.2f}\n"
                t += f"  1/4 {item.nombre_producto[:20]}\n"
                t += f"  1/4 {item.nombre_cuarto_2[:20]}\n"
                t += f"  1/4 {item.nombre_cuarto_3[:20]}\n"
                t += f"  1/4 {item.nombre_cuarto_4[:20]}\n"
            elif getattr(item, 'mitad_producto', None):
                t += f"{item.cantidad}x MITAD/MITAD    {subt_base:>8.2f}\n"
                t += f"  1/2 {item.nombre_producto[:20]}\n"
                mitad_nombre = item.mitad_producto.nombre if hasattr(item.mitad_producto, 'nombre') else str(item.mitad_producto)
                t += f"  1/2 {mitad_nombre[:20]}\n"
            else:
                nombre = item.nombre_producto[:20]
                t += f"{item.cantidad}x {nombre:<20} {subt_base:>8.2f}\n"
            
            if hasattr(item, 'extras'):
                for ex in item.extras.all():
                    porcion_txt = getattr(ex, 'porcion_display', '')
                    precio_ex = to_decimal(ex.precio) * item.cantidad
                    nombre_extra_formateado = f"{porcion_txt}{ex.nombre_extra}".lower()[:14]
                    if precio_ex > 0:
                        t += f"  EXTRA {nombre_extra_formateado:<14} {precio_ex:>8.2f}\n"
                    else:
                        t += f"  EXTRA {nombre_extra_formateado}\n"

        t += "--------------------------------\n"
        t += f"TOTAL USD:           ${total_usd:>8.2f}\n"
        t += f"TOTAL Bs.:         {total_bs:>11.2f}\n"
        t += "--------------------------------\n"
        t += f"RECIBIDO USD:        ${monto_recibido:>8.2f}\n"
        
        if vuelto_usd > 0:
            t += f"VUELTO USD:          ${vuelto_usd:>8.2f}\n"
        if propina > 0:
            t += f"PROPINA:             ${propina:>8.2f}\n"
            
        t += "================================\n"
        t += f"{config.mensaje_ticket.center(32)}\n"
        t += "\n\n\x1D\x56\x41\x10"

        return enviar_a_spooler(config.impresora_ticket, t, "Factura")
    except Exception as e:
        print(f"Error Factura: {e}")
        return False, str(e)

# --- REPETIR LA MISMA LÓGICA EN LA PRECUENTA ---

def imprimir_precuenta(orden, tasa_valor_ignorado):
    """ Función para la PRE-CUENTA """
    config = Configuracion.get_solo()
    if not config.impresora_ticket: return False, "No hay impresora"

    try:
        # Ignoramos el parámetro enviado y buscamos la tasa real nosotros
        tasa = obtener_tasa_real()
        
        t = ""
        t += f"{config.nombre_empresa.upper().center(32)}\n"
        t += "       *** PRE-CUENTA *** \n"
        hora_local = timezone.localtime(timezone.now())
        t += f"MESA: {orden.mesa.number} | {hora_local.strftime('%H:%M')}\n"
        t += "--------------------------------\n"
        
        total_usd = Decimal('0.00')
        for item in orden.detalles.all():
            p_base = to_decimal(item.precio_unitario)
            c_extras = sum(to_decimal(e.precio) for e in item.extras_elegidos.all())
            subtotal_linea = (p_base + c_extras) * item.cantidad
            total_usd += subtotal_linea
            
            subtotal_base = p_base * item.cantidad
            
            if getattr(item, 'cuarto_2_producto', None):
                t += f"{item.cantidad}x 4 ESTACIONES   {subtotal_base:>8.2f}\n"
                t += f"  1/4 {item.producto.nombre[:20]}\n"
                t += f"  1/4 {item.cuarto_2_producto.nombre[:20]}\n"
                t += f"  1/4 {item.cuarto_3_producto.nombre[:20]}\n"
                t += f"  1/4 {item.cuarto_4_producto.nombre[:20]}\n"
            elif getattr(item, 'mitad_producto', None):
                t += f"{item.cantidad}x MITAD/MITAD    {subtotal_base:>8.2f}\n"
                t += f"  1/2 {item.producto.nombre[:20]}\n"
                t += f"  1/2 {item.mitad_producto.nombre[:20]}\n"
            else:
                nom = item.producto.nombre
                if item.producto.tamano != 'UNI':
                    nom += f" ({item.producto.get_tamano_display()})"
                nom = nom[:20]
                t += f"{item.cantidad}x {nom:<20} {subtotal_base:>8.2f}\n"
                
            for ex in item.extras_elegidos.all():
                porcion_txt = getattr(ex, 'porcion_display', '')
                precio_ex = to_decimal(ex.precio) * item.cantidad
                nombre_extra_formateado = f"{porcion_txt}{ex.insumo.nombre}".lower()[:14]
                if precio_ex > 0:
                    t += f"  EXTRA {nombre_extra_formateado:<14} {precio_ex:>8.2f}\n"
                else:
                    t += f"  EXTRA {nombre_extra_formateado}\n"

        total_bs = (total_usd * tasa).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        t += "--------------------------------\n"
        t += f"SUBTOTAL USD:        ${total_usd:>8.2f}\n"
        t += "\n"
        t += "     TOTAL A PAGAR:     \n"
        t += f"  USD: ${total_usd:>15.2f}\n"
        t += f"  Bs.: {total_bs:>16.2f}\n"
        t += "--------------------------------\n"
        t += "      PAGO EN BOLIVARES:      \n"
        t += "    ACEPTAMOS PAGO MOVIL Y    \n"
        t += "       PUNTO DE VENTA.        \n"
        t += " LA PROPIONA NO ESTA INCLUIDA \n"
        t += "\n\n\x1D\x56\x41\x10"

        return enviar_a_spooler(config.impresora_ticket, t, "Precuenta")
    except Exception as e:
        print(f"Error Precuenta: {e}")
        return False, str(e)

def imprimir_comanda(orden):
    config = Configuracion.get_solo()
    if not config.impresora_ticket: return False, "No hay impresora"
    try:
        t = "================================\n      COMANDA DE COCINA       \n================================\n"
        tipo = getattr(orden, 'tipo_servicio', 'MESA')
        if tipo == 'LLEVAR': t += ">>> PARA LLEVAR <<<\n"
        elif tipo == 'DOMICILIO': t += ">>> DELIVERY <<<\n"
        else: t += f"MESA: {orden.mesa.number}\n"
        hora_local = timezone.localtime(timezone.now())
        t += f"Ticket: #{orden.id} | Mesero: {orden.mesero.username.upper() if orden.mesero else 'CAJA'}\n"
        t += f"Hora: {hora_local.strftime('%H:%M')}\n--------------------------------\n\n"
        for item in orden.detalles.all():
            if getattr(item, 'cuarto_2_producto', None):
                tamano_txt = f" ({item.producto.get_tamano_display().upper()})" if item.producto.tamano != 'UNI' else ""
                t += f"{item.cantidad}x 4 ESTACIONES{tamano_txt}\n"
                t += f"   >> 1/4 {item.producto.nombre.upper()}\n"
                t += f"   >> 1/4 {item.cuarto_2_producto.nombre.upper()}\n"
                t += f"   >> 1/4 {item.cuarto_3_producto.nombre.upper()}\n"
                t += f"   >> 1/4 {item.cuarto_4_producto.nombre.upper()}\n"
            elif getattr(item, 'mitad_producto', None):
                tamano_txt = f" ({item.producto.get_tamano_display().upper()})" if item.producto.tamano != 'UNI' else ""
                t += f"{item.cantidad}x MITAD{tamano_txt}\n"
                t += f"   >> 1/2 {item.producto.nombre.upper()}\n"
                t += f"   >> 1/2 {item.mitad_producto.nombre.upper()}\n"
            else:
                tamano_txt = f" ({item.producto.get_tamano_display().upper()})" if item.producto.tamano != 'UNI' else ""
                t += f"{item.cantidad}x {item.producto.nombre.upper()}{tamano_txt}\n"
            
            for extra in item.extras_elegidos.all(): 
                nombre_ext = f"{extra.porcion_display}{extra.insumo.nombre.upper()}"[:22]
                t += f"   EXTRA {nombre_ext}\n"
            if getattr(item, 'ingredientes_removidos', None) and item.ingredientes_removidos.exists():
                for rem in item.ingredientes_removidos.all(): t += f"   - SIN {rem.nombre.upper()}\n"
            if hasattr(item, 'removidos_detalles'):
                for r in item.removidos_detalles.all():
                    porcion_str = "1/4 " if r.porcion == Decimal('0.25') else "1/2 " if r.porcion == Decimal('0.50') else "3/4 " if r.porcion == Decimal('0.75') else ""
                    nombre_rem = getattr(r.insumo, 'nombre', '') if hasattr(r, 'insumo') else getattr(r, 'nombre_insumo', '')
                    t += f"   - SIN {porcion_str}{nombre_rem.upper()}\n"
            if getattr(item, 'es_para_llevar', False): t += "   [PARA LLEVAR]\n"
            if getattr(item, 'nota', None): t += f"   ** {item.nota} **\n"
        t += "--------------------------------\n\n\x1D\x56\x41\x10"
        return enviar_a_spooler(config.impresora_ticket, t, "Comanda")
    except Exception as e:
        print(f"Error comanda: {e}"); return False, str(e)

def imprimir_consumo_interno(consumo):
    """ Imprime el ticket de cocina/caja para la comida de personal y regalos """
    config = Configuracion.get_solo()
    if not config.impresora_ticket: return False, "No hay impresora"
    try:
        t = "================================\n"
        if consumo.tipo == 'PERSONAL':
            t += "      COMIDA DE PERSONAL      \n"
        elif consumo.tipo == 'CORTESIA':
            t += "      CORTESIA / REGALO       \n"
        else:
            t += f"      {consumo.get_tipo_display().upper()}      \n"
        t += "================================\n"
        hora_local = timezone.localtime(timezone.now())
        t += f"Ticket: #{consumo.id} | Solicita: {consumo.usuario.username.upper() if consumo.usuario else 'SISTEMA'}\n"
        t += f"Hora: {hora_local.strftime('%H:%M')}\n--------------------------------\n\n"
        
        t += f"DETALLE:\n{consumo.descripcion.upper()}\n\n"
        
        if consumo.tipo == 'PERSONAL':
            from inventory.models import MovimientoInventario
            movs = MovimientoInventario.objects.filter(nota=f"Extra Personal #{consumo.id}")
            if movs.exists():
                t += "EXTRAS:\n"
                for mov in movs: t += f"   EXTRA {mov.insumo.nombre.upper()[:22]}\n"
        t += "--------------------------------\n\n\x1D\x56\x41\x10"
        return enviar_a_spooler(config.impresora_ticket, t, "Consumo Interno")
    except Exception as e:
        print(f"Error comanda interna: {e}"); return False, str(e)

def _imprimir_en_segundo_plano(nombre_impresora, texto, titulo_doc):
    try:
        hPrinter = win32print.OpenPrinter(nombre_impresora)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, (titulo_doc, None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, texto.encode('cp850', errors='replace'))
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"Error Spooler Background: {e}")

def enviar_a_spooler(nombre_impresora, texto, titulo_doc):
    try:
        # Lanzamos la impresión en un hilo secundario para que no bloquee el sistema
        hilo = threading.Thread(target=_imprimir_en_segundo_plano, args=(nombre_impresora, texto, titulo_doc))
        hilo.start()
        return True, "Enviado a cola de impresión"
    except Exception as e:
        print(f"Error Spooler: {e}"); return False, str(e)