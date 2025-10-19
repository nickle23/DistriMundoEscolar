# database.py - COMPATIBLE CON SQLite (local) Y PostgreSQL (Render) - VERSIÓN CORREGIDA
import os
import json
from datetime import datetime

# Determinar qué base de datos usar
def get_database_config():
    """Configura la base de datos según el entorno"""
    if os.environ.get('RENDER'):
        # En Render: usar PostgreSQL
        print("🔄 Conectando a PostgreSQL (Render)")
        import psycopg
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise Exception("❌ DATABASE_URL no configurada en Render")
        return {
            'type': 'postgresql',
            'connector': psycopg,
            'url': database_url
        }
    else:
        # En local: usar SQLite
        print("🔄 Conectando a SQLite (Local)")
        import sqlite3
        return {
            'type': 'sqlite', 
            'connector': sqlite3,
            'file': 'distrimundo.db'
        }

def get_db_connection():
    """Conexión universal para SQLite y PostgreSQL - VERSIÓN SIMPLIFICADA"""
    config = get_database_config()
    
    try:
        if config['type'] == 'sqlite':
            # Conexión SQLite (local)
            conn = config['connector'].connect(config['file'], check_same_thread=False)
            conn.row_factory = config['connector'].Row
            return conn
        else:
            # Conexión PostgreSQL (Render) - psycopg3 es más simple
            conn = config['connector'].connect(config['url'])
            return conn
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        raise

def execute_query(query, params=None):
    """Ejecuta consultas en ambas bases de datos - VERSIÓN MEJORADA"""
    conn = None
    try:
        conn = get_db_connection()
        
        if isinstance(conn, tuple):  # PostgreSQL con cursor separado
            conn, cur = conn
            cur.execute(query, params or ())
            result = cur.fetchall() if query.strip().upper().startswith('SELECT') else None
            conn.commit()
            return result, cur
        else:  # SQLite
            cursor = conn.execute(query, params or ())
            result = cursor.fetchall() if query.strip().upper().startswith('SELECT') else None
            conn.commit()
            return result, cursor
            
    except Exception as e:
        print(f"❌ Error en consulta: {e}")
        raise
    finally:
        if conn and not isinstance(conn, tuple):
            conn.close()

def init_db():
    """Inicializa la base de datos (funciona en ambos)"""
    print("🔄 Inicializando base de datos...")
    
    try:
        # Tabla de vendedores
        execute_query('''
            CREATE TABLE IF NOT EXISTS vendedores (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                device_id TEXT,
                activo BOOLEAN DEFAULT TRUE,
                es_admin BOOLEAN DEFAULT FALSE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TIMESTAMP,
                accesos_totales INTEGER DEFAULT 0
            )
        ''')
        
        # Tabla de historial de accesos
        execute_query('''
            CREATE TABLE IF NOT EXISTS accesos (
                id SERIAL PRIMARY KEY,
                vendedor_id TEXT NOT NULL,
                dispositivo TEXT NOT NULL,
                exitoso BOOLEAN NOT NULL,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip TEXT
            )
        ''')
        
        # Tabla de sesiones activas
        execute_query('''
            CREATE TABLE IF NOT EXISTS sesiones_activas (
                sesion_id TEXT PRIMARY KEY,
                vendedor_id TEXT NOT NULL,
                dispositivo TEXT NOT NULL,
                ip TEXT NOT NULL,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP,
                activa BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Insertar admin por defecto si no existe
        result, cursor = execute_query('SELECT COUNT(*) as count FROM vendedores WHERE codigo = %s', ('DARKEYES',))
        
        # Manejar diferentes tipos de resultado
        if result:
            count = result[0][0] if isinstance(result[0], (list, tuple)) else result[0]['count']
        else:
            count = 0
        
        if count == 0:
            execute_query('''
                INSERT INTO vendedores 
                (codigo, nombre, device_id, activo, es_admin, fecha_creacion, accesos_totales)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                'DARKEYES',
                'Administrador Principal',
                '',
                True,
                True,
                datetime.now().isoformat(),
                0
            ))
            print("✅ Admin DARKEYES creado")
        
        print("✅ Base de datos inicializada correctamente")
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

# Funciones de respaldo (solo para compatibilidad con app.py)
def sincronizar_sqlite_a_json():
    """Función de compatibilidad - en PostgreSQL no es necesaria"""
    print("ℹ️  En PostgreSQL, la sincronización a JSON no es necesaria")
    return True

def restaurar_desde_json():
    """Función de compatibilidad - en PostgreSQL no es necesaria"""
    print("ℹ️  En PostgreSQL, la restauración desde JSON no es necesaria")
    return False

def migrar_datos_json():
    """Función de compatibilidad"""
    print("ℹ️  En PostgreSQL, la migración desde JSON no es necesaria")
    return

# Inicializar la base de datos al importar
if __name__ != "__main__":
    init_db()