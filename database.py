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

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla vendedores
    cursor.execute('''
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
    
    # Insertar admin si no existe
    cursor.execute("SELECT COUNT(*) FROM vendedores WHERE codigo = 'DARKEYES'")
    count = cursor.fetchone()[0]
    
    if count == 0:
        cursor.execute('''
            INSERT INTO vendedores (codigo, nombre, device_id, activo, es_admin, fecha_creacion, accesos_totales)
            VALUES ('DARKEYES', 'Administrador Principal', '', TRUE, TRUE, %s, 0)
        ''', (datetime.now().isoformat(),))
    
    conn.commit()
    conn.close()

# Inicializar la base de datos
if __name__ != "__main__":
    init_db()