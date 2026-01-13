import sqlite3

# Nombre de tu base de datos
db_name = "db.sqlite3"

print(f"🔌 Conectando a {db_name}...")
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

try:
    # Intento 1: Borrar solo la columna problemática (Funciona en SQLite modernos)
    print("INTENTO 1: Eliminando columna 'es_para_llevar'...")
    cursor.execute("ALTER TABLE tables_detalleorden DROP COLUMN es_para_llevar")
    print("✅ ¡ÉXITO! Columna eliminada. El sistema debería funcionar.")

except sqlite3.OperationalError as e:
    # Si falla (SQLite viejo), plan B: Borrar la tabla para que Django la recree
    print(f"⚠️ Aviso: {e}")
    print("INTENTO 2: La versión de SQLite es antigua. Borrando tabla 'tables_detalleorden'...")
    cursor.execute("DROP TABLE IF EXISTS tables_detalleorden")
    print("✅ Tabla borrada. Ahora debes ejecutar 'python manage.py migrate' para recrearla.")

conn.commit()
conn.close()