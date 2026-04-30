from core.models import Configuracion
from tables.models import TasaBCV  # <--- IMPORTANTE: Importamos el modelo de la tasa real
import win32print
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
        t += f"FECHA: {venta.fecha.strftime('%d/%m/%Y %H:%M')}\n"
        t += f"MESA: {venta.mesa_numero} | MESERO: {venta.mesero.username.upper() if venta.mesero else 'CAJA'}\n"
        t += "--------------------------------\n"
        t += "CANT  DESCRIPCION         TOTAL\n"
        t += "--------------------------------\n"

        for item in venta.detalles.all():
            nombre = item.nombre_producto[:15]
            subt_item = to_decimal(item.subtotal)
            linea = f"{item.cantidad}x {nombre:<15} {subt_item:>8.2f}\n"
            t += linea
            
            if hasattr(item, 'extras'):
                for ex in item.extras.all():
                    t += f"  + {ex.nombre_extra[:20].lower()}\n"

        t += "--------------------------------\n"
        t += f"TOTAL USD:           ${total_usd:>8.2f}\n"
        t += f"TASA BCV:             {tasa:>8.2f}\n"
        t += f"TOTAL Bs.:         {total_bs:>11.2f}\n"
        t += "--------------------------------\n"
        t += f"RECIBIDO USD:        ${monto_recibido:>8.2f}\n"
        
        if vuelto_usd > 0:
            t += f"VUELTO USD:          ${vuelto_usd:>8.2f}\n"
        if propina > 0:
            t += f"PROPINA:             ${propina:>8.2f}\n"
            
        t += "================================\n"
        t += f"{config.mensaje_ticket.center(32)}\n"
        t += "\n\n\n\n\n\x1D\x56\x41\x10"

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
        t += f"MESA: {orden.mesa.number} | {timezone.now().strftime('%H:%M')}\n"
        t += "--------------------------------\n"
        
        total_usd = Decimal('0.00')
        for item in orden.detalles.all():
            p_base = to_decimal(item.precio_unitario)
            c_extras = sum(to_decimal(e.precio) for e in item.extras_elegidos.all())
            subtotal_linea = (p_base + c_extras) * item.cantidad
            total_usd += subtotal_linea
            
            nom = item.producto.nombre[:15]
            t += f"{item.cantidad}x {nom:<15} {subtotal_linea:>8.2f}\n"
            for ex in item.extras_elegidos.all():
                t += f"  + {ex.insumo.nombre[:20].lower()}\n"

        total_bs = (total_usd * tasa).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        t += "--------------------------------\n"
        t += f"SUBTOTAL USD:        ${total_usd:>8.2f}\n"
        t += f"TASA REF:             {tasa:>8.2f}\n"
        t += "\n"
        t += "     TOTAL A PAGAR:     \n"
        t += f"  USD: ${total_usd:>15.2f}\n"
        t += f"  Bs.: {total_bs:>16.2f}\n"
        t += "--------------------------------\n"
        t += "      PAGO EN BOLIVARES:      \n"
        t += "    ACEPTAMOS PAGO MOVIL Y    \n"
        t += "       PUNTO DE VENTA.        \n"
        t += "\n\n\n\n\n\x1D\x56\x41\x10"

        return enviar_a_spooler(config.impresora_ticket, t, "Precuenta")
    except Exception as e:
        print(f"Error Precuenta: {e}")
        return False, str(e)

def imprimir_comanda(orden):
    config = Configuracion.get_solo()
    if not config.impresora_ticket: return False, "No hay impresora"
    try:
        t = "\n================================\n      COMANDA DE COCINA       \n================================\n"
        tipo = getattr(orden, 'tipo_servicio', 'MESA')
        if tipo == 'LLEVAR': t += ">>> PARA LLEVAR <<<\n"
        elif tipo == 'DOMICILIO': t += ">>> DELIVERY <<<\n"
        else: t += f"MESA: {orden.mesa.number}\n"
        t += f"Ticket: #{orden.id} | Mesero: {orden.mesero.username.upper() if orden.mesero else 'CAJA'}\n"
        t += f"Hora: {timezone.now().strftime('%H:%M')}\n--------------------------------\n\n"
        for item in orden.detalles.all():
            t += f"{item.cantidad}x {item.producto.nombre.upper()}\n"
            for extra in item.extras_elegidos.all(): t += f"   + {extra.insumo.nombre.upper()}\n"
            if getattr(item, 'es_para_llevar', False): t += "   [EMPACAR PARA LLEVAR]\n"
            if getattr(item, 'nota', None): t += f"   ** {item.nota} **\n"
            t += "\n"
        t += "--------------------------------\n\n\n\n\n\n\x1D\x56\x41\x10"
        return enviar_a_spooler(config.impresora_ticket, t, "Comanda")
    except Exception as e:
        print(f"Error comanda: {e}"); return False, str(e)

def enviar_a_spooler(nombre_impresora, texto, titulo_doc):
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
        return True, "Ok"
    except Exception as e:
        print(f"Error Spooler: {e}"); return False, str(e)