import requests
from bs4 import BeautifulSoup
import urllib3
from django.utils import timezone
from .models import TasaBCV # Importamos el modelo que acabamos de crear
from core.models import Configuracion

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_tasa_bcv():
    """
    Lógica inteligente:
    1. Revisa si ya tenemos una tasa guardada de HOY.
    2. Si existe, la devuelve (Rápido).
    3. Si no existe o es vieja, hace scraping (Lento), la guarda y la devuelve.
    """
    config = Configuracion.get_solo()
    
    if not config.usar_scraping_bcv:
        # Si el scraping está desactivado, usamos la tasa guardada manualmente
        ultima_tasa = TasaBCV.objects.order_by('-fecha_actualizacion').first()
        if not ultima_tasa or ultima_tasa.precio != config.tasa_dolar:
            TasaBCV.objects.create(precio=config.tasa_dolar)
        return f"{config.tasa_dolar} Bs/S (Manual)"
    
    # --- 1. INTENTO DE BASE DE DATOS ---
    # Buscamos la última tasa guardada
    ultima_tasa = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    
    if ultima_tasa:
        # Permitimos múltiples actualizaciones al día.
        # En lugar de 1 por día, limitamos a 1 consulta cada HORA (3600 segundos).
        # Esto evita que el BCV bloquee tu IP por exceso de peticiones.
        tiempo_transcurrido = timezone.now() - ultima_tasa.fecha_actualizacion
        if tiempo_transcurrido.total_seconds() < 3600:
            # Excepción: Si el precio en BD es idéntico al manual, forzamos la actualización inmediata.
            if ultima_tasa.precio != config.tasa_dolar:
                return f"{ultima_tasa.precio}"

    # --- 2. INTENTO DE SCRAPING (Conexión a Internet) ---
    print("Actualizando tasa desde BCV (Internet)...")
    url = 'https://www.bcv.org.ve'
    
    try:
        # Agregamos cabeceras (User-Agent) porque el BCV bloquea peticiones de bots (HTTP 403)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, verify=False, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        contenedor = soup.find(id='dolar')
        
        if contenedor:
            dolar_tag = contenedor.find('strong')
            if dolar_tag:
                texto_crudo = dolar_tag.get_text().strip()
                texto_punto = texto_crudo.replace(',', '.')
                valor_float = float(texto_punto)

                # --- 3. GUARDAMOS EN BASE DE DATOS ---
                # Guardamos siempre para mantener el historial (auditoría) solicitado
                TasaBCV.objects.create(precio=valor_float)

                return f"{valor_float:.2f} Bs/S"
                
    except Exception as e:
        print(f"Error scraping: {e}")
        # Si falla el scraping, intentamos devolver la vieja aunque no sea de hoy
        if ultima_tasa:
             return f"{ultima_tasa.precio} Bs/S"
        return "Sin conexión"