import win32print

# ¡CAMBIA ESTO POR EL NOMBRE EXACTO DE TU IMPRESORA!
# Cópialo tal cual aparece en "Impresoras y escáneres" de Windows
nombre_impresora = "POS-58" 

try:
    print(f"Buscando la impresora: {nombre_impresora}...")
    hPrinter = win32print.OpenPrinter(nombre_impresora)
    
    print("Enviando orden...")
    hJob = win32print.StartDocPrinter(hPrinter, 1, ("Prueba de conexion", None, "RAW"))
    win32print.StartPagePrinter(hPrinter)
    
    win32print.WritePrinter(hPrinter, b"HOLA MUNDO. ESTO ES UNA PRUEBA DE IMPRESION\n\n\n\n\n\x1D\x56\x41\x10")
    
    win32print.EndPagePrinter(hPrinter)
    win32print.EndDocPrinter(hPrinter)
    win32print.ClosePrinter(hPrinter)
    
    print("¡Exito! Revisa si salió el papel.")
except Exception as e:
    print(f"Error crítico: {e}")