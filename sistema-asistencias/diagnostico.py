import sqlite3
import os
from datetime import datetime

print("🔍 DIAGNÓSTICO COMPLETO DEL SISTEMA")
print("=" * 50)

# 1. Verificar si la base de datos existe
db_path = 'asistencias.db'
if os.path.exists(db_path):
    print("✅ Base de datos EXISTE")
    file_size = os.path.getsize(db_path)
    print(f"   Tamaño: {file_size} bytes")
else:
    print("❌ Base de datos NO EXISTE")
    exit()

try:
    # 2. Intentar conexión CON row_factory
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # ← ESTA LÍNEA FALTA
    cursor = conn.cursor()
    print("✅ Conexión a BD establecida")
    
    # 3. Verificar tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = cursor.fetchall()
    print("📋 Tablas encontradas:")
    for tabla in tablas:
        print(f"   - {tabla['name']}")
    
    # 4. Verificar trabajadores
    cursor.execute("SELECT COUNT(*) as count FROM trabajadores")
    count_trab = cursor.fetchone()['count']
    print(f"👥 Trabajadores en BD: {count_trab}")
    
    if count_trab > 0:
        cursor.execute("SELECT dni, nombre FROM trabajadores LIMIT 5")
        trabajadores = cursor.fetchall()
        print("   Primeros trabajadores:")
        for trab in trabajadores:
            print(f"     - {trab['dni']}: {trab['nombre']}")
    
    # 5. Verificar asistencias
    cursor.execute("SELECT COUNT(*) as count FROM asistencias")
    count_asis = cursor.fetchone()['count']
    print(f"📅 Total asistencias: {count_asis}")
    
    # 6. Verificar asistencias de hoy
    hoy = datetime.now().date()
    cursor.execute("SELECT COUNT(*) as count FROM asistencias WHERE fecha = ?", (hoy,))
    count_hoy = cursor.fetchone()['count']
    print(f"   Asistencias HOY ({hoy}): {count_hoy}")
    
    if count_hoy > 0:
        cursor.execute("SELECT dni, entrada, salida, estado FROM asistencias WHERE fecha = ?", (hoy,))
        asistencias = cursor.fetchall()
        print("   Detalle de hoy:")
        for asis in asistencias:
            print(f"     - {asis['dni']}: {asis['entrada']} a {asis['salida']} [{asis['estado']}]")
    
    conn.close()
    print("🎉 Diagnóstico COMPLETADO - BD FUNCIONAL")
    
except Exception as e:
    print(f"❌ ERROR en base de datos: {e}")