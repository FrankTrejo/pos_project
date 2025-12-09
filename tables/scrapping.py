import requests
from bs4 import BeautifulSoup
import urllib3
import re

# Suprimimos las advertencias de seguridad por usar verify=False
# Esto es importante para no llenar la consola de Django de ruido.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_tasa_bcv():
    """
    Se conecta a la página del BCV, extrae la tasa del dólar actual
    y la retorna como un string limpio.
    Retorna un mensaje de error si algo falla durante el proceso.
    """
    URL = 'https://www.bcv.org.ve'
    
    # 1. Definimos un valor por defecto en caso de que algo salga mal.
    # Este es el valor que verá el usuario si el scraping falla.
    tasa_resultado = "Sin conexión BCV"

    try:
        #print("Iniciando petición al BCV...") # Opcional para depurar
        
        # Realizamos la petición
        # verify=False es necesario para el BCV, aunque no es ideal en producción,
        # es la única forma de que funcione con su certificado actual.
        response = requests.get(URL, verify=False, timeout=10)
        response.raise_for_status() # Lanza error si la respuesta no es OK (200)

        # Si llegamos aquí, hubo conexión exitosa. Analizamos el HTML.
        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscamos el contenedor específico
        contenedor = soup.find(id='dolar')
        
        if contenedor:
            # Buscamos la etiqueta strong dentro del contenedor
            dolar_tag = contenedor.find('strong')
            
            # --- NUEVO CÓDIGO CON REDONDEO ---
            if dolar_tag:
                try:
                    # 1. Obtener texto crudo (ej: "36,4567" o "36,4521")
                    texto_crudo = dolar_tag.get_text().strip()

                    # 2. Reemplazar coma por punto para poder convertir a número
                    texto_con_punto = texto_crudo.replace(',', '.')

                    # 3. Convertir de texto a número decimal (float)
                    valor_float = float(texto_con_punto)

                    # 4. Formatear a string con exactamente 2 decimales.
                    # La sintaxis f"{valor:.2f}" hace el redondeo automáticamente.
                    # Si es 36.4567 -> pasa a "36.46"
                    # Si es 36.4521 -> pasa a "36.45"
                    texto_redondeado_punto = f"{valor_float:.2f}"

                    # 5. Volver a poner la coma para la visualización final en español
                    texto_final_coma = texto_redondeado_punto.replace('.', ',')

                    tasa_resultado = f"{texto_final_coma} Bs/S (BCV)"

                except ValueError:
                    # Por si el BCV pone algo que no sea un número en ese lugar
                    tasa_resultado = "Error: Tasa no numérica"
            else:
                tasa_resultado = "Formato BCV cambió (tag)"
        else:
             print("Scraping error: No se encontró el contenedor con id='dolar'")
             tasa_resultado = "Formato BCV cambió"

    except requests.exceptions.RequestException as e:
        # Capturamos errores de conexión (timeout, DNS, etc.)
        print(f'Error al realizar la petición al BCV: {e}')
        # tasa_resultado mantiene su valor por defecto "Sin conexión BCV"
    except Exception as e:
        # Capturamos cualquier otro error inesperado durante el parsing
        print(f'Error inesperado en el scraping: {e}')
        tasa_resultado = "Error procesando tasa"

    # 3. FINALMENTE, RETORNAMOS EL RESULTADO
    # Esta línea es fundamental. La función devuelve el string final a la vista de Django.
    return tasa_resultado

# ==========================================
# Bloque de prueba
# ==========================================
# Este 'if' permite probar si este archivo funciona ejecutándolo directamente
# desde la terminal (python scrapping.py) sin tener que correr todo Django.
if __name__ == "__main__":
    print("--- Probando función de scraping aislada ---")
    resultado = obtener_tasa_bcv()
    print(f"Resultado final obtenido: '{resultado}'")