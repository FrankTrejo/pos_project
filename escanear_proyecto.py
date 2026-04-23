from pathlib import Path

def consolidar_codigo(ruta_base, archivo_salida='codigo_completo.txt'):
    ruta = Path(ruta_base)
    extensiones_codigo = ['.py', '.html', '.js', '.css']
    carpetas_ignoradas = ['venv', 'env', '__pycache__', 'migrations', '.git']

    # Abrimos el archivo de salida para empezar a escribir
    with open(archivo_salida, 'w', encoding='utf-8') as salida:
        salida.write("=== CÓDIGO DEL SISTEMA DE FACTURACIÓN ===\n\n")

        for archivo in ruta.rglob('*'):
            if archivo.is_file() and archivo.suffix in extensiones_codigo:
                if not any(carpeta in archivo.parts for carpeta in carpetas_ignoradas):
                    try:
                        with open(archivo, 'r', encoding='utf-8') as f:
                            contenido = f.read()
                        
                        # Escribimos un encabezado visible para cada archivo
                        salida.write(f"\n{'='*50}\n")
                        salida.write(f"📁 ARCHIVO: {archivo.relative_to(ruta)}\n")
                        salida.write(f"{'='*50}\n\n")
                        
                        # Pegamos el código
                        salida.write(contenido)
                        salida.write("\n")
                        
                    except Exception as e:
                        salida.write(f"\n[No se pudo leer {archivo.name}: {e}]\n")
    
    print(f"✅ ¡Listo! Todo el código se ha guardado en: {archivo_salida}")

if __name__ == "__main__":
    consolidar_codigo('.')