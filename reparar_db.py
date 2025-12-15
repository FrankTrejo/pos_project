import sqlite3

# Nombre de tu base de datos
db_name = "db.sqlite3"

try:
    print(f"🔌 Conectando a {db_name}...")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # 1. Verificar qué columnas existen realmente
    print("🔍 Inspeccionando tabla 'tables_producto'...")
    cursor.execute("PRAGMA table_info(tables_producto)")
    columnas = [col[1] for col in cursor.fetchall()]
    print(f"   Columnas encontradas: {columnas}")

    # 2. Si falta la columna, la creamos a la fuerza
    if 'costo_materia_prima' not in columnas:
        print("⚠️ La columna 'costo_materia_prima' NO existe. Creándola ahora...")
        cursor.execute("ALTER TABLE tables_producto ADD COLUMN costo_materia_prima decimal DEFAULT 0;")
        conn.commit()
        print("✅ ¡COLUMNA CREADA CON ÉXITO!")
    else:
        print("ℹ️ La columna YA existe. El problema podría ser otro.")

    conn.close()

except Exception as e:
    print(f"❌ Error crítico: {e}")