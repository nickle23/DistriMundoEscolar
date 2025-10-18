# database.py
import sqlite3
import os
import json
from datetime import datetime

def get_db_connection():
    """Establece conexión con la base de datos SQLite"""
    conn = sqlite3.connect('distrimundo.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
    return conn

def sincronizar_sqlite_a_json():
    """Sincroniza datos de SQLite a JSON como respaldo - MEJORADA"""
    try:
        conn = get_db_connection()
        vendedores = conn.execute('SELECT * FROM vendedores').fetchall()
        conn.close()
        
        # Convertir a formato JSON compatible
        vendedores_dict = {}
        for v in vendedores:
            vendedores_dict[v['codigo']] = dict(v)
        
        # Guardar respaldo con metadatos
        backup_data = {
            'fecha_sincronizacion': datetime.now().isoformat(),
            'total_vendedores': len(vendedores_dict),
            'vendedores': vendedores_dict
        }
        
        with open('vendedores_backup.json', 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Sincronizado: {len(vendedores_dict)} vendedores a JSON")
        return True
        
    except Exception as e:
        print(f"❌ Error sincronizando: {e}")
        return False

def restaurar_desde_json():
    """Restaura datos desde JSON - MEJORADA para Render"""
    try:
        if not os.path.exists('vendedores_backup.json'):
            print("📝 No hay archivo de respaldo para restaurar")
            return False
            
        with open('vendedores_backup.json', 'r', encoding='utf-8') as f:
            backup = json.load(f)
        
        # Verificar que el backup tenga datos válidos
        if 'vendedores' not in backup or not backup['vendedores']:
            print("⚠️  Backup vacío o inválido")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # En Render, SIEMPRE limpiar y restaurar completamente
        if os.environ.get('RENDER'):
            print("🔄 Render: Limpiando y restaurando desde respaldo...")
            cursor.execute('DELETE FROM vendedores')
        
        # Restaurar vendedores
        vendedores_restaurados = 0
        for codigo, datos in backup['vendedores'].items():
            cursor.execute('''
                INSERT OR REPLACE INTO vendedores 
                (codigo, nombre, device_id, activo, es_admin, fecha_creacion, ultimo_acceso, accesos_totales)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            vendedores_restaurados += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Restaurados {vendedores_restaurados} vendedores desde JSON")
        return True
        
    except Exception as e:
        print(f"❌ Error restaurando desde JSON: {e}")
        return False

def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    try:
        conn = get_db_connection()
        
        # Tabla de vendedores
        conn.execute('''
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS accesos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id TEXT NOT NULL,
                dispositivo TEXT NOT NULL,
                exitoso BOOLEAN NOT NULL,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip TEXT,
                FOREIGN KEY (vendedor_id) REFERENCES vendedores (codigo)
            )
        ''')
        
        # Tabla de sesiones activas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sesiones_activas (
                sesion_id TEXT PRIMARY KEY,
                vendedor_id TEXT NOT NULL,
                dispositivo TEXT NOT NULL,
                ip TEXT NOT NULL,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP,
                activa BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (vendedor_id) REFERENCES vendedores (codigo)
            )
        ''')
        
        conn.commit()
        
        # Insertar admin por defecto si no existe
        cursor = conn.execute('SELECT COUNT(*) as count FROM vendedores WHERE codigo = "DARKEYES"')
        if cursor.fetchone()['count'] == 0:
            conn.execute('''
                INSERT INTO vendedores 
                (codigo, nombre, device_id, activo, es_admin, fecha_creacion, accesos_totales)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'DARKEYES',
                'Administrador Principal',
                '',
                True,
                True,
                datetime.now().isoformat(),
                0
            ))
            conn.commit()
            print("✅ Admin DARKEYES creado")
        
        conn.close()
        print("✅ Base de datos inicializada correctamente")
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

def migrar_datos_json():
    """Migra los datos existentes de JSON a SQLite"""
    try:
        # Migrar vendedores
        if os.path.exists('vendedores.json'):
            with open('vendedores.json', 'r', encoding='utf-8') as f:
                vendedores = json.load(f)
                
            conn = get_db_connection()
            for codigo, datos in vendedores.items():
                # Verificar si el vendedor ya existe
                cursor = conn.execute('SELECT COUNT(*) as count FROM vendedores WHERE codigo = ?', (codigo,))
                if cursor.fetchone()['count'] == 0:
                    conn.execute('''
                        INSERT INTO vendedores 
                        (codigo, nombre, device_id, activo, es_admin, fecha_creacion, ultimo_acceso, accesos_totales)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.commit()
            conn.close()
            print("✅ Vendedores migrados a SQLite")
        
        # Migrar accesos (si existe)
        if os.path.exists('accesos.json'):
            with open('accesos.json', 'r', encoding='utf-8') as f:
                accesos = json.load(f)
                
            conn = get_db_connection()
            for acceso in accesos:
                conn.execute('''
                    INSERT INTO accesos 
                    (vendedor_id, dispositivo, exitoso, fecha_hora, ip)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    acceso['vendedor_id'],
                    acceso['dispositivo'],
                    acceso['exitoso'],
                    acceso['fecha_hora'],
                    acceso.get('ip', '')
                ))
            conn.commit()
            conn.close()
            print("✅ Accesos migrados a SQLite")
        
        # Migrar sesiones activas (si existe)
        if os.path.exists('sesiones_activas.json'):
            with open('sesiones_activas.json', 'r', encoding='utf-8') as f:
                sesiones = json.load(f)
                
            conn = get_db_connection()
            for sesion_id, datos in sesiones.items():
                # Verificar si la sesión ya existe
                cursor = conn.execute('SELECT COUNT(*) as count FROM sesiones_activas WHERE sesion_id = ?', (sesion_id,))
                if cursor.fetchone()['count'] == 0:
                    conn.execute('''
                        INSERT INTO sesiones_activas 
                        (sesion_id, vendedor_id, dispositivo, ip, fecha_inicio, fecha_fin, activa)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        sesion_id,
                        datos['vendedor_id'],
                        datos['dispositivo'],
                        datos['ip'],
                        datos['fecha_inicio'],
                        datos.get('fecha_fin'),
                        datos.get('activa', True)
                    ))
            conn.commit()
            conn.close()
            print("✅ Sesiones migradas a SQLite")
            
    except Exception as e:
        print(f"❌ Error en migración de datos: {e}")

# ⚠️ IMPORTANTE: COMENTAR LAS SIGUIENTES LÍNEAS PARA EVITAR INICIALIZACIÓN DUPLICADA
# init_db()
# migrar_datos_json()
