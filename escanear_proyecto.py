import os

# CONFIGURACIÓN
# Nombre del archivo de salida
output_file = "codigo_completo.txt"

# Carpetas y archivos que NO queremos leer (para no llenar de basura)
ignore_dirs = ['__pycache__', 'migrations', 'venv', 'env', '.git', '.idea', 'static', 'media']
ignore_files = ['db.sqlite3', 'escanear_proyecto.py', 'codigo_completo.txt', '.DS_Store']
accepted_extensions = ['.py', '.html', '.css', '.js']

def is_ignored(path, names):
    return [n for n in names if n in ignore_dirs or n in ignore_files]

def scan_project():
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Recorremos todas las carpetas
        for root, dirs, files in os.walk("."):
            # Filtramos carpetas ignoradas
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if file in ignore_files:
                    continue
                
                # Solo leemos archivos de código
                if not any(file.endswith(ext) for ext in accepted_extensions):
                    continue

                file_path = os.path.join(root, file)
                
                # Escribimos el nombre del archivo para saber cuál es
                outfile.write(f"\n{'='*50}\n")
                outfile.write(f"ARCHIVO: {file_path}\n")
                outfile.write(f"{'='*50}\n")
                
                # Escribimos el contenido del archivo
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"[No se pudo leer el archivo: {e}]\n")

    print(f"¡Listo! Todo tu código se guardó en '{output_file}'.")
    print("Ahora sube ese archivo al chat o copia su contenido.")

if __name__ == "__main__":
    scan_project()