import sqlite3
import os

def verificar_estado_sistema():
    print("🔍 VERIFICACIÓN COMPLETA DEL SISTEMA")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('asistencias.db')
        cursor = conn.cursor()
        
        # Trabajadores
        cursor.execute("SELECT COUNT(*) FROM trabajadores")
        total_trabajadores = cursor.fetchone()[0]
        print(f"👥 TRABAJADORES: {total_trabajadores}")
        
        # Asistencias totales
        cursor.execute("SELECT COUNT(*) FROM asistencias")
        total_asistencias = cursor.fetchone()[0]
        print(f"📊 ASISTENCIAS TOTALES: {total_asistencias}")
        
        # Registros huérfanos
        cursor.execute('''
            SELECT COUNT(*) FROM asistencias 
            WHERE dni NOT IN (SELECT dni FROM trabajadores)
        ''')
        registros_huérfanos = cursor.fetchone()[0]
        print(f"👻 REGISTROS HUÉRFANOS: {registros_huérfanos}")
        
        # Detalle de huérfanos
        if registros_huérfanos > 0:
            cursor.execute('''
                SELECT DISTINCT dni, COUNT(*) as total 
                FROM asistencias 
                WHERE dni NOT IN (SELECT dni FROM trabajadores)
                GROUP BY dni
            ''')
            print("   DNIs huérfanos encontrados:")
            for row in cursor.fetchall():
                print(f"     - {row[0]}: {row[1]} registros")
        
        conn.close()
        
        # Verificar archivos offline
        print("\n🗂️ ARCHIVOS OFFLINE:")
        offline_dir = 'data_offline'
        if os.path.exists(offline_dir):
            archivos = [f for f in os.listdir(offline_dir) if f.endswith('.json')]
            print(f"   Total archivos: {len(archivos)}")
            for archivo in archivos:
                print(f"     - {archivo}")
        else:
            print("   ℹ️ No existe directorio data_offline")
        
        print("\n🎯 RECOMENDACIONES:")
        if registros_huérfanos > 0:
            print("   ❌ Ejecutar: Limpiar Registros Huérfanos desde el Panel Admin")
        else:
            print("   ✅ Sistema limpio y funcionando correctamente")
            
    except Exception as e:
        print(f"❌ Error en verificación: {e}")

if __name__ == '__main__':
    verificar_estado_sistema()