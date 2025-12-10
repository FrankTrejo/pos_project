import requests
from bs4 import BeautifulSoup
import urllib3
from django.utils import timezone
from .models import TasaBCV # Importamos el modelo que acabamos de crear

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_tasa_bcv():
    """
    Lógica inteligente:
    1. Revisa si ya tenemos una tasa guardada de HOY.
    2. Si existe, la devuelve (Rápido).
    3. Si no existe o es vieja, hace scraping (Lento), la guarda y la devuelve.
    """
    
    # --- 1. INTENTO DE BASE DE DATOS ---
    # Buscamos la última tasa guardada
    ultima_tasa = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    
    if ultima_tasa:
        # Verificamos si es de hoy
        hoy = timezone.now().date()
        if ultima_tasa.fecha_actualizacion.date() == hoy:
            # ¡Éxito! Devolvemos la de la BD y nos ahorramos la conexión lenta
            return f"{ultima_tasa.precio}"

    # --- 2. INTENTO DE SCRAPING (Solo si no hay datos de hoy) ---
    print("Actualizando tasa desde BCV (Internet)...")
    url = 'https://www.bcv.org.ve'
    
    try:
        response = requests.get(url, verify=False, timeout=10)
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
                # Creamos el registro nuevo para no volver a consultar hoy
                TasaBCV.objects.create(precio=valor_float)

                return f"{valor_float:.2f} Bs/S"
                
    except Exception as e:
        print(f"Error scraping: {e}")
        # Si falla el scraping, intentamos devolver la vieja aunque no sea de hoy
        if ultima_tasa:
             return f"{ultima_tasa.precio} Bs/S"
        return "Sin conexión"