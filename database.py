import os
import sqlite3
from datetime import datetime

def get_db_connection():
    if os.environ.get('RENDER'):
        # PostgreSQL en Render con psycopg3
        import psycopg
        conn = psycopg.connect(os.environ.get('DATABASE_URL'))
        return conn
    else:
        # SQLite en local
        conn = sqlite3.connect('distrimundo.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def get_param_placeholder():
    """Devuelve el placeholder correcto según la base de datos"""
    return '%s' if os.environ.get('RENDER') else '?'

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    param = get_param_placeholder()
    
    # Tabla vendedores
    if os.environ.get('RENDER'):
        # PostgreSQL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendedores (
                codigo VARCHAR(50) PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                device_id VARCHAR(100),
                activo BOOLEAN DEFAULT TRUE,
                es_admin BOOLEAN DEFAULT FALSE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TIMESTAMP,
                accesos_totales INTEGER DEFAULT 0
            )
        ''')
    else:
        # SQLite
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendedores (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                device_id TEXT,
                activo BOOLEAN DEFAULT 1,
                es_admin BOOLEAN DEFAULT 0,
                fecha_creacion TIMESTAMP,
                ultimo_acceso TIMESTAMP,
                accesos_totales INTEGER DEFAULT 0
            )
        ''')
    
    # TABLA SESIONES_ACTIVAS (CRÍTICA PARA LA SEGURIDAD)
    if os.environ.get('RENDER'):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sesiones_activas (
                id SERIAL PRIMARY KEY,
                sesion_id VARCHAR(200) NOT NULL,
                vendedor_id VARCHAR(50) NOT NULL,
                dispositivo VARCHAR(100) NOT NULL,
                ip VARCHAR(50),
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP,
                activa BOOLEAN DEFAULT TRUE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sesiones_activas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sesion_id TEXT NOT NULL,
                vendedor_id TEXT NOT NULL,
                dispositivo TEXT NOT NULL,
                ip TEXT,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP,
                activa BOOLEAN DEFAULT 1
            )
        ''')
    
    # TABLA ACCESOS (para historial)
    if os.environ.get('RENDER'):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accesos (
                id SERIAL PRIMARY KEY,
                vendedor_id VARCHAR(50) NOT NULL,
                dispositivo VARCHAR(100),
                exitoso BOOLEAN DEFAULT FALSE,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip VARCHAR(50)
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accesos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id TEXT NOT NULL,
                dispositivo TEXT,
                exitoso BOOLEAN DEFAULT 0,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip TEXT
            )
        ''')
    
    # Insertar admin si no existe
    cursor.execute(f"SELECT COUNT(*) FROM vendedores WHERE codigo = 'DARKEYES'")
    count = cursor.fetchone()[0]
    
    if count == 0:
        cursor.execute(f'''
            INSERT INTO vendedores (codigo, nombre, device_id, activo, es_admin, fecha_creacion, accesos_totales)
            VALUES ({param}, {param}, {param}, {param}, {param}, {param}, {param})
        ''', ('DARKEYES', 'Administrador Principal', '', True, True, datetime.now().isoformat(), 0))
    
    conn.commit()
    conn.close()

# Inicializar la base de datos
if __name__ != "__main__":
    init_db()