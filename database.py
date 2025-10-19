# database.py - COMPATIBLE CON SQLite (local) Y PostgreSQL (Render)
import os
import json
from datetime import datetime

# Determinar qué base de datos usar
def get_database_config():
    """Configura la base de datos según el entorno"""
    if os.environ.get('RENDER'):
        # En Render: usar PostgreSQL
        print("🔄 Conectando a PostgreSQL (Render)")
        import psycopg2
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise Exception("❌ DATABASE_URL no configurada en Render")
        return {
            'type': 'postgresql',
            'connector': psycopg2,
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
    """Conexión universal para SQLite y PostgreSQL"""
    config = get_database_config()
    
    try:
        if config['type'] == 'sqlite':
            # Conexión SQLite (local)
            conn = config['connector'].connect(config['file'], check_same_thread=False)
            conn.row_factory = config['connector'].Row
            return conn
        else:
            # Conexión PostgreSQL (Render)
            import psycopg2.extras
            conn = config['connector'].connect(config['url'])
            # Crear un cursor que devuelva diccionarios
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            return conn, cur
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        raise

def execute_query(query, params=None):
    """Ejecuta consultas en ambas bases de datos"""
    config = get_database_config()
    
    if config['type'] == 'sqlite':
        # SQLite
        conn = get_db_connection()
        cursor = conn.execute(query, params or ())
        result = cursor.fetchall() if query.strip().upper().startswith('SELECT') else None
        conn.commit()
        if not query.strip().upper().startswith('SELECT'):
            conn.close()
        return result, cursor
    else:
        # PostgreSQL
        conn, cur = get_db_connection()
        cur.execute(query, params or ())
        result = cur.fetchall() if query.strip().upper().startswith('SELECT') else None
        conn.commit()
        cur.close()
        conn.close()
        return result, cur

def init_db():
    """Inicializa la base de datos (funciona en ambos)"""
    print("🔄 Inicializando base de datos...")
    
    config = get_database_config()
    
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
        
        count = result[0]['count'] if result else 0
        
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

# Funciones específicas para SQLite (solo locales)
def sincronizar_sqlite_a_json():
    """Sincroniza datos a JSON como respaldo (solo para SQLite local)"""
    try:
        if not os.environ.get('RENDER'):  # Solo en local
            result, cursor = execute_query('SELECT * FROM vendedores')
            vendedores = result or []
            
            vendedores_dict = {}
            for v in vendedores:
                vendedores_dict[v['codigo']] = dict(v)
            
            with open('vendedores_backup.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_sincronizacion': datetime.now().isoformat(),
                    'vendedores': vendedores_dict
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Sincronizado: {len(vendedores_dict)} vendedores a JSON")
            
    except Exception as e:
        print(f"❌ Error sincronizando: {e}")

def migrar_datos_json():
    """Migra datos de JSON a la base de datos (solo local)"""
    if os.environ.get('RENDER'):
        return  # En Render no migrar desde JSON
        
    try:
        if os.path.exists('vendedores.json'):
            with open('vendedores.json', 'r', encoding='utf-8') as f:
                vendedores = json.load(f)
                
            for codigo, datos in vendedores.items():
                result, cursor = execute_query('SELECT COUNT(*) as count FROM vendedores WHERE codigo = %s', (codigo,))
                count = result[0]['count'] if result else 0
                
                if count == 0:
                    execute_query('''
                        INSERT INTO vendedores 
                        (codigo, nombre, device_id, activo, es_admin, fecha_creacion, ultimo_acceso, accesos_totales)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        codigo,
                        datos['nombre'],
                        datos.get('device_id', ''),
                        datos.get('activo', True),
                        datos.get('es_admin', False),
                        datos.get('fecha_creacion', datetime.now().isoformat()),
                        datos.get('ultimo_acceso'),
                        datos.get('accesos_totales', 0)
                    ))
            print("✅ Vendedores migrados a la base de datos")
            
    except Exception as e:
        print(f"❌ Error en migración de datos: {e}")

# Inicializar la base de datos al importar
if __name__ != "__main__":
    init_db()