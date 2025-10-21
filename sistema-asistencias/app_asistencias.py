from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import sqlite3
import json
import os
import requests

# OBTENER LA RUTA ABSOLUTA de la carpeta actual
base_dir = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(base_dir, 'templates')

from flask import Blueprint

# Crear Blueprint en lugar de app Flask
app_asistencias = Blueprint('asistencias', __name__, 
    template_folder=template_folder,
    static_folder=os.path.join(base_dir, 'static')
)

# Cambiar todas las @app.route por @app_asistencias.route
app.secret_key = 'clave_secreta_asistencias_2024'

print(f"✅ Templates folder: {template_folder}")
print("✅ Sistema de Asistencias HÍBRIDO 100% Automático iniciado")

# ================= CONFIGURACIÓN DE HORARIOS =================
HORAS_JORNADA_NORMAL = 11  # 8:00 AM a 7:00 PM = 11 horas
HORA_ENTRADA_ESTABLECIDA = datetime.strptime("08:00", "%H:%M").time()
HORA_SALIDA_ESTABLECIDA = datetime.strptime("19:00", "%H:%M").time()
HORA_TOLERANCIA = datetime.strptime("08:15", "%H:%M").time()  # 15 minutos de tolerancia
MINUTOS_TOLERANCIA = 15

print(f"⏰ Horario establecido: {HORA_ENTRADA_ESTABLECIDA.strftime('%H:%M')} a {HORA_SALIDA_ESTABLECIDA.strftime('%H:%M')}")
print(f"⏰ Tolerancia: {MINUTOS_TOLERANCIA} minutos (hasta {HORA_TOLERANCIA.strftime('%H:%M')})")

# Base de datos
def get_db_connection():
    conn = sqlite3.connect('asistencias.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de trabajadores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trabajadores (
            dni TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT,
            fecha_ingreso DATE,
            sueldo_base REAL DEFAULT 0,
            activo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de asistencias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dni TEXT NOT NULL,
            fecha DATE NOT NULL,
            entrada TIME,
            salida TIME,
            horas_trabajadas REAL DEFAULT 0,
            horas_extras REAL DEFAULT 0,
            estado TEXT DEFAULT 'PENDIENTE',
            observaciones TEXT,
            tipo_registro TEXT DEFAULT 'ONLINE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dni) REFERENCES trabajadores (dni),
            UNIQUE(dni, fecha)
        )
    ''')
    
    # Tabla de configuración del sistema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_sistema (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            horas_jornada_normal INTEGER DEFAULT 11,
            hora_entrada TIME DEFAULT '08:00',
            hora_salida TIME DEFAULT '19:00',
            tolerancia_minutos INTEGER DEFAULT 15,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertar configuración por defecto si no existe
    cursor.execute("SELECT COUNT(*) FROM config_sistema")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO config_sistema (id, horas_jornada_normal, hora_entrada, hora_salida, tolerancia_minutos)
            VALUES (1, 11, '08:00', '19:00', 15)
        ''')
    
    # Insertar trabajadores de ejemplo si no existen
    cursor.execute("SELECT COUNT(*) FROM trabajadores")
    if cursor.fetchone()[0] == 0:
        trabajadores_ejemplo = [
            ('12345678', 'Juan Pérez García', 'Vendedor Senior', 'Ventas', '2023-01-15', 1800.00),
            ('87654321', 'María García López', 'Vendedor', 'Ventas', '2023-03-20', 1500.00),
            ('11223344', 'Carlos Rodríguez', 'Almacenero', 'Logística', '2023-06-10', 1600.00)
        ]
        cursor.executemany(
            "INSERT INTO trabajadores (dni, nombre, cargo, area, fecha_ingreso, sueldo_base) VALUES (?, ?, ?, ?, ?, ?)",
            trabajadores_ejemplo
        )
        print("✅ Trabajadores de ejemplo insertados")
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")

# ================= FUNCIÓN PARA DETERMINAR ESTADO =================
def determinar_estado(entrada_str):
    """Determina el estado basado en la hora de entrada"""
    if not entrada_str:
        return 'FALTA'
    
    try:
        # Si es un objeto time, convertirlo a string
        if hasattr(entrada_str, 'strftime'):
            entrada_str = entrada_str.strftime('%H:%M:%S')
        
        entrada_time = datetime.strptime(entrada_str, '%H:%M:%S').time()
        tolerancia_time = HORA_TOLERANCIA
        
        if entrada_time <= tolerancia_time:
            return 'NORMAL'
        else:
            return 'TARDE'
    except Exception as e:
        print(f"⚠️ Error determinando estado: {e}")
        return 'NORMAL'

# ================= SISTEMA OFFLINE MEJORADO =================
def verificar_conexion():
    """Verifica si hay conexión a internet"""
    try:
        # Intentar hacer una petición rápida a un servidor confiable
        response = requests.get('http://www.google.com', timeout=5)
        return True
    except:
        return False

def guardar_localmente(dni, tipo, fecha, hora):
    """Guarda la marcación localmente cuando no hay internet - MEJORADO"""
    try:
        if not os.path.exists('data_offline'):
            os.makedirs('data_offline')
        
        # Formatear hora correctamente (sin microsegundos)
        if hasattr(hora, 'strftime'):
            hora_str = hora.strftime('%H:%M:%S')
        else:
            hora_str = str(hora)
            if '.' in hora_str:
                hora_str = hora_str.split('.')[0]  # Eliminar microsegundos
        
        registro = {
            'dni': dni,
            'tipo': tipo,
            'fecha': fecha.isoformat(),
            'hora': hora_str,
            'timestamp': datetime.now().isoformat(),
            'intentos_sincronizacion': 0
        }
        
        archivo = f'data_offline/{dni}_pendientes.json'
        
        registros = []
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                try:
                    registros = json.load(f)
                except:
                    registros = []
        
        registros.append(registro)
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Registro offline guardado: {dni} - {tipo} - {hora_str}")
        return True
        
    except Exception as e:
        print(f"❌ Error guardando offline: {e}")
        return False

def sincronizar_registros_offline():
    """Sincroniza todos los registros offline cuando hay internet - MEJORADO"""
    try:
        if not os.path.exists('data_offline'):
            return {'success': True, 'sincronizados': 0, 'pendientes': 0}
        
        archivos = [f for f in os.listdir('data_offline') if f.endswith('_pendientes.json')]
        total_sincronizados = 0
        total_pendientes = 0
        
        for archivo in archivos:
            archivo_path = os.path.join('data_offline', archivo)
            
            with open(archivo_path, 'r', encoding='utf-8') as f:
                registros = json.load(f)
            
            nuevos_registros = []
            
            for registro in registros:
                dni = registro['dni']
                tipo = registro['tipo']
                fecha = datetime.fromisoformat(registro['fecha']).date()
                hora_str = registro['hora']
                
                # Convertir hora a formato válido
                try:
                    if '.' in hora_str:
                        hora_str = hora_str.split('.')[0]  # Eliminar microsegundos
                    hora = datetime.strptime(hora_str, '%H:%M:%S').time()
                except Exception as e:
                    print(f"❌ Error parseando hora {hora_str}: {e}")
                    nuevos_registros.append(registro)
                    total_pendientes += 1
                    continue
                
                # Incrementar contador de intentos
                registro['intentos_sincronizacion'] = registro.get('intentos_sincronizacion', 0) + 1
                
                if sincronizar_registro(dni, tipo, fecha, hora):
                    total_sincronizados += 1
                    print(f"✅ Sincronizado: {dni} - {tipo} - {fecha} - {hora_str}")
                else:
                    # Si ha tenido más de 10 intentos fallidos, lo marcamos como problema
                    if registro['intentos_sincronizacion'] < 10:
                        nuevos_registros.append(registro)
                        total_pendientes += 1
                    else:
                        print(f"⚠️ Registro con muchos intentos fallidos: {dni}")
                        # Guardar en archivo de errores
                        guardar_registro_error(registro)
            
            if nuevos_registros:
                with open(archivo_path, 'w', encoding='utf-8') as f:
                    json.dump(nuevos_registros, f, ensure_ascii=False, indent=2)
            else:
                os.remove(archivo_path)
                print(f"🗑️ Archivo {archivo} eliminado (todo sincronizado)")
        
        print(f"📊 Sincronización completada: {total_sincronizados} sincronizados, {total_pendientes} pendientes")
        return {
            'success': True, 
            'sincronizados': total_sincronizados, 
            'pendientes': total_pendientes
        }
        
    except Exception as e:
        print(f"❌ Error sincronizando offline: {e}")
        return {'success': False, 'error': str(e)}

def guardar_registro_error(registro):
    """Guarda registros problemáticos para revisión manual"""
    try:
        if not os.path.exists('data_offline'):
            os.makedirs('data_offline')
        
        archivo_errores = 'data_offline/registros_con_error.json'
        errores = []
        
        if os.path.exists(archivo_errores):
            with open(archivo_errores, 'r', encoding='utf-8') as f:
                try:
                    errores = json.load(f)
                except:
                    errores = []
        
        registro['fecha_error'] = datetime.now().isoformat()
        errores.append(registro)
        
        with open(archivo_errores, 'w', encoding='utf-8') as f:
            json.dump(errores, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"❌ Error guardando registro con error: {e}")

def sincronizar_registro(dni, tipo, fecha, hora):
    """Sincroniza un registro individual con la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el trabajador existe
        cursor.execute("SELECT nombre FROM trabajadores WHERE dni = ?", (dni,))
        trabajador = cursor.fetchone()
        
        if not trabajador:
            print(f"❌ Trabajador {dni} no existe en BD")
            conn.close()
            return False
        
        # Formatear hora correctamente
        hora_str = hora.strftime('%H:%M:%S')
        
        if tipo == 'entrada':
            # Determinar estado basado en la hora
            estado = determinar_estado(hora)
            cursor.execute(
                "INSERT OR REPLACE INTO asistencias (dni, fecha, entrada, estado, tipo_registro) VALUES (?, ?, ?, ?, ?)",
                (dni, fecha, hora_str, estado, 'OFFLINE_SINCRONIZADO')
            )
        else:  # salida
            # Buscar entrada del mismo día
            cursor.execute(
                "SELECT * FROM asistencias WHERE dni = ? AND fecha = ? AND entrada IS NOT NULL",
                (dni, fecha)
            )
            registro = cursor.fetchone()
            
            if registro:
                entrada_time = datetime.strptime(registro['entrada'], '%H:%M:%S').time()
                entrada_dt = datetime.combine(fecha, entrada_time)
                salida_dt = datetime.combine(fecha, hora)
                
                # Si la salida es antes que la entrada, asumir día siguiente
                if salida_dt < entrada_dt:
                    salida_dt = salida_dt + timedelta(days=1)
                
                horas_trabajadas = (salida_dt - entrada_dt).total_seconds() / 3600
                horas_extras = max(0, horas_trabajadas - HORAS_JORNADA_NORMAL)
                
                cursor.execute(
                    "UPDATE asistencias SET salida = ?, horas_trabajadas = ?, horas_extras = ?, estado = 'COMPLETO', tipo_registro = ? WHERE dni = ? AND fecha = ?",
                    (hora_str, round(horas_trabajadas, 2), round(horas_extras, 2), 'OFFLINE_SINCRONIZADO', dni, fecha)
                )
            else:
                # No hay entrada, crear registro solo con salida
                cursor.execute(
                    "INSERT INTO asistencias (dni, fecha, salida, estado, tipo_registro) VALUES (?, ?, ?, ?, ?)",
                    (dni, fecha, hora_str, 'SOLO_SALIDA', 'OFFLINE_SINCRONIZADO')
                )
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error sincronizando registro {dni}: {e}")
        return False

# ================= CÁLCULO DE HORAS EXTRAS Y SUELDOS =================

def calcular_pago_horas_extras(dni, mes, anio):
    """Calcular el pago de horas extras según la fórmula especificada"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT sueldo_base FROM trabajadores WHERE dni = ?", (dni,))
    trabajador = cursor.fetchone()
    
    if not trabajador:
        conn.close()
        return 0, 0, 0
    
    sueldo_base = trabajador['sueldo_base']
    
    cursor.execute('''
        SELECT SUM(horas_extras) as total_horas_extras
        FROM asistencias 
        WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
    ''', (dni, str(anio), str(mes).zfill(2)))
    
    resultado = cursor.fetchone()
    total_horas_extras = resultado['total_horas_extras'] or 0
    
    pago_por_dia = sueldo_base / 30
    pago_por_hora = pago_por_dia / 11
    total_pagar = round(pago_por_hora * total_horas_extras, 2)
    
    conn.close()
    
    return total_horas_extras, pago_por_hora, total_pagar

def obtener_resumen_mensual(dni, mes, anio):
    """Obtener resumen completo del mes para un trabajador"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM trabajadores WHERE dni = ?", (dni,))
    trabajador = cursor.fetchone()
    
    if not trabajador:
        conn.close()
        return None
    
    # Estadísticas del mes
    cursor.execute('''
        SELECT 
            COUNT(*) as dias_laborables,
            SUM(CASE WHEN entrada IS NOT NULL THEN 1 ELSE 0 END) as dias_trabajados,
            SUM(CASE WHEN entrada IS NULL AND salida IS NULL THEN 1 ELSE 0 END) as faltas,
            SUM(CASE WHEN estado = 'TARDE' THEN 1 ELSE 0 END) as tardanzas,
            SUM(horas_trabajadas) as total_horas_normales,
            SUM(horas_extras) as total_horas_extras
        FROM asistencias 
        WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
    ''', (dni, str(anio), str(mes).zfill(2)))
    
    stats = cursor.fetchone()
    
    # Detalle día por día
    cursor.execute('''
        SELECT fecha, entrada, salida, horas_trabajadas, horas_extras, observaciones, estado
        FROM asistencias 
        WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
        ORDER BY fecha
    ''', (dni, str(anio), str(mes).zfill(2)))
    
    detalle = []
    for row in cursor.fetchall():
        detalle.append(dict(row))
    
    horas_extras, pago_por_hora, total_pagar = calcular_pago_horas_extras(dni, mes, anio)
    
    conn.close()
    
    return {
        'trabajador': dict(trabajador),
        'estadisticas': {
            'dias_laborables': stats['dias_laborables'] or 0,
            'dias_trabajados': stats['dias_trabajados'] or 0,
            'faltas': stats['faltas'] or 0,
            'tardanzas': stats['tardanzas'] or 0,
            'total_horas_normales': stats['total_horas_normales'] or 0,
            'total_horas_extras': horas_extras
        },
        'pago_horas_extras': {
            'pago_por_hora': pago_por_hora,
            'total_pagar': total_pagar
        },
        'detalle_diario': detalle
    }

# ================= RUTAS PRINCIPALES MEJORADAS =================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/estado-conexion')
def estado_conexion():
    """Endpoint para verificar el estado de la conexión"""
    tiene_conexion = verificar_conexion()
    return jsonify({
        'conexion': tiene_conexion,
        'servidor': 'online',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/sincronizar', methods=['POST'])
def sincronizar():
    """Sincroniza registros offline automáticamente"""
    try:
        resultado = sincronizar_registros_offline()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error sincronizando: {str(e)}'})

@app.route('/info-pendientes')
def info_pendientes():
    """Obtener información de registros pendientes de sincronización"""
    try:
        if not os.path.exists('data_offline'):
            return jsonify({'pendientes': 0, 'archivos': []})
        
        archivos = [f for f in os.listdir('data_offline') if f.endswith('_pendientes.json')]
        total_pendientes = 0
        info_archivos = []
        
        for archivo in archivos:
            archivo_path = os.path.join('data_offline', archivo)
            with open(archivo_path, 'r', encoding='utf-8') as f:
                registros = json.load(f)
                total_pendientes += len(registros)
                info_archivos.append({
                    'archivo': archivo,
                    'registros': len(registros),
                    'dni': archivo.replace('_pendientes.json', '')
                })
        
        return jsonify({
            'pendientes': total_pendientes,
            'archivos': info_archivos,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/marcar', methods=['POST'])
def marcar_asistencia():
    """Marcar asistencia - SISTEMA HÍBRIDO 100% AUTOMÁTICO"""
    try:
        data = request.get_json()
        dni = data.get('dni', '').strip()
        tipo = data.get('tipo', '').strip().lower()
        
        print(f"🎯 SOLICITUD MARCACIÓN - DNI: {dni}, TIPO: {tipo}")
        
        # Validaciones básicas
        if not dni or len(dni) != 8:
            return jsonify({'success': False, 'mensaje': 'DNI debe tener 8 dígitos'})
        
        if tipo not in ['entrada', 'salida']:
            return jsonify({'success': False, 'mensaje': 'Tipo de marcación inválido'})
        
        fecha_actual = datetime.now().date()
        hora_actual = datetime.now().strftime('%H:%M:%S')
        hora_actual_obj = datetime.now().time()
        
        print(f"📅 Fecha: {fecha_actual}, Hora: {hora_actual}")
        
        # PRIMERO: Intentar sincronizar registros pendientes si hay conexión
        if verificar_conexion():
            resultado_sincronizacion = sincronizar_registros_offline()
            if resultado_sincronizacion.get('sincronizados', 0) > 0:
                print(f"🔄 Sincronizados {resultado_sincronizacion['sincronizados']} registros pendientes automáticamente")
        
        # SEGUNDO: Intentar guardar en base de datos (modo online)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # VERIFICAR TRABAJADOR
            cursor.execute("SELECT nombre FROM trabajadores WHERE dni = ?", (dni,))
            trabajador = cursor.fetchone()
            
            if not trabajador:
                conn.close()
                # Si no existe el trabajador, guardar offline
                guardar_localmente(dni, tipo, fecha_actual, hora_actual_obj)
                return jsonify({
                    'success': True, 
                    'offline': True,
                    'mensaje': f'⚠️ Trabajador no encontrado - Guardado offline: {tipo.upper()} {hora_actual[:-3]}'
                })
            
            nombre = trabajador['nombre']
            print(f"✅ Trabajador: {nombre}")
            
            if tipo == 'entrada':
                # Verificar si ya marcó entrada
                cursor.execute(
                    "SELECT id FROM asistencias WHERE dni = ? AND fecha = ? AND entrada IS NOT NULL", 
                    (dni, fecha_actual)
                )
                if cursor.fetchone():
                    conn.close()
                    return jsonify({'success': False, 'mensaje': 'Ya marcaste entrada hoy'})
                
                # Determinar estado
                if hora_actual_obj <= HORA_TOLERANCIA:
                    estado = 'NORMAL'
                    mensaje = f'✅ {nombre} - Entrada: {hora_actual[:-3]}'
                else:
                    estado = 'TARDE' 
                    mensaje = f'⚠️ {nombre} - Entrada TARDÍA: {hora_actual[:-3]}'
                
                # Insertar entrada
                cursor.execute(
                    "INSERT INTO asistencias (dni, fecha, entrada, estado) VALUES (?, ?, ?, ?)",
                    (dni, fecha_actual, hora_actual, estado)
                )
                
            else:  # SALIDA
                # Buscar entrada de hoy
                cursor.execute(
                    "SELECT id, entrada FROM asistencias WHERE dni = ? AND fecha = ? AND entrada IS NOT NULL AND salida IS NULL",
                    (dni, fecha_actual)
                )
                registro = cursor.fetchone()
                
                if not registro:
                    conn.close()
                    # Si no hay entrada, guardar solo salida offline
                    guardar_localmente(dni, tipo, fecha_actual, hora_actual_obj)
                    return jsonify({
                        'success': True, 
                        'offline': True,
                        'mensaje': f'⚠️ Sin entrada - Guardado offline: SALIDA {hora_actual[:-3]}'
                    })
                
                # Calcular horas
                entrada_dt = datetime.strptime(registro['entrada'], '%H:%M:%S')
                salida_dt = datetime.strptime(hora_actual, '%H:%M:%S')
                
                # Si la salida es antes que la entrada, asumir día siguiente
                if salida_dt < entrada_dt:
                    salida_dt = salida_dt.replace(day=salida_dt.day + 1)
                
                diff = salida_dt - entrada_dt
                horas_trabajadas = diff.total_seconds() / 3600
                horas_extras = max(0, horas_trabajadas - HORAS_JORNADA_NORMAL)
                
                # Actualizar salida
                cursor.execute(
                    "UPDATE asistencias SET salida = ?, horas_trabajadas = ?, horas_extras = ?, estado = 'COMPLETO' WHERE id = ?",
                    (hora_actual, round(horas_trabajadas, 2), round(horas_extras, 2), registro['id'])
                )
                
                mensaje = f'✅ {nombre} - Salida: {hora_actual[:-3]} - Horas: {horas_trabajadas:.1f}'
            
            # CONFIRMAR
            conn.commit()
            conn.close()
            
            print(f"🎉 MARCACIÓN ONLINE EXITOSA: {mensaje}")
            return jsonify({'success': True, 'offline': False, 'mensaje': mensaje})
            
        except Exception as e:
            print(f"❌ Error en modo online, cambiando a offline: {e}")
            # Si falla la BD, guardar offline
            guardar_localmente(dni, tipo, fecha_actual, hora_actual_obj)
            return jsonify({
                'success': True, 
                'offline': True,
                'mensaje': f'⚠️ Sin conexión - Guardado offline: {tipo.upper()} {hora_actual[:-3]}'
            })
        
    except Exception as e:
        print(f"💥 ERROR GENERAL: {e}")
        # Último recurso: guardar offline
        try:
            fecha_actual = datetime.now().date()
            hora_actual_obj = datetime.now().time()
            guardar_localmente(dni, tipo, fecha_actual, hora_actual_obj)
            return jsonify({
                'success': True, 
                'offline': True,
                'mensaje': f'⚠️ Error - Guardado offline: {tipo.upper()} {datetime.now().strftime("%H:%M")}'
            })
        except:
            return jsonify({'success': False, 'mensaje': f'Error crítico: {str(e)}'})

# ================= RUTAS DEL PANEL ADMIN =================

@app.route('/admin')
def admin_panel():
    """Panel de control administrativo"""
    return render_template('admin.html')

@app.route('/admin/estadisticas')
def admin_estadisticas():
    """Obtener estadísticas para el dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM trabajadores WHERE activo = TRUE")
    total_trabajadores = cursor.fetchone()[0]
    
    fecha_hoy = datetime.now().date()
    
    cursor.execute(
        "SELECT COUNT(DISTINCT dni) FROM asistencias WHERE fecha = ? AND entrada IS NOT NULL",
        (fecha_hoy,)
    )
    presentes_hoy = cursor.fetchone()[0]
    
    faltas_hoy = total_trabajadores - presentes_hoy
    
    cursor.execute(
        "SELECT COUNT(*) FROM asistencias WHERE fecha = ? AND estado = 'TARDE'",
        (fecha_hoy,)
    )
    tardanzas_hoy = cursor.fetchone()[0]
    
    # Obtener info de pendientes offline
    info_pendientes_data = info_pendientes()
    pendientes_data = info_pendientes_data.get_json()
    pendientes_offline = pendientes_data.get('pendientes', 0) if not pendientes_data.get('error') else 0
    
    conn.close()
    
    return jsonify({
        'total_trabajadores': total_trabajadores,
        'presentes_hoy': presentes_hoy,
        'tardanzas_hoy': tardanzas_hoy,
        'faltas_hoy': faltas_hoy,
        'pendientes_offline': pendientes_offline,
        'conexion': verificar_conexion()
    })

@app.route('/admin/asistencias-hoy')
def admin_asistencias_hoy():
    """Obtener asistencias del día actual"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    fecha_hoy = datetime.now().date()
    
    cursor.execute('''
        SELECT t.dni, t.nombre, a.entrada, a.salida, a.horas_trabajadas, a.horas_extras, a.fecha, a.estado, a.tipo_registro
        FROM trabajadores t
        LEFT JOIN asistencias a ON t.dni = a.dni AND a.fecha = ?
        WHERE t.activo = TRUE
        ORDER BY t.nombre
    ''', (fecha_hoy,))
    
    asistencias = []
    for row in cursor.fetchall():
        estado = row['estado'] if row['estado'] else 'FALTA'
        tipo_registro = row['tipo_registro'] if row['tipo_registro'] else 'NO_REGISTRADO'
        
        asistencias.append({
            'dni': row['dni'],
            'nombre': row['nombre'],
            'fecha': row['fecha'],
            'entrada': row['entrada'],
            'salida': row['salida'],
            'horas_trabajadas': row['horas_trabajadas'],
            'horas_extras': row['horas_extras'],
            'estado': estado,
            'tipo_registro': tipo_registro
        })
    
    conn.close()
    return jsonify(asistencias)

@app.route('/admin/trabajadores')
def admin_trabajadores():
    """Obtener lista de todos los trabajadores"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT dni, nombre, cargo, area, fecha_ingreso, sueldo_base, activo
        FROM trabajadores 
        ORDER BY nombre
    ''')
    
    trabajadores = []
    for row in cursor.fetchall():
        trabajadores.append(dict(row))
    
    conn.close()
    return jsonify(trabajadores)

@app.route('/admin/agregar-trabajador', methods=['POST'])
def admin_agregar_trabajador():
    """Agregar nuevo trabajador"""
    try:
        data = request.get_json()
        dni = data.get('dni')
        nombre = data.get('nombre')
        cargo = data.get('cargo')
        area = data.get('area')
        fecha_ingreso = data.get('fecha_ingreso')
        sueldo_base = data.get('sueldo_base')
        
        if not dni or not nombre or not cargo:
            return jsonify({'success': False, 'mensaje': 'DNI, nombre y cargo son requeridos'})
        
        if len(dni) != 8:
            return jsonify({'success': False, 'mensaje': 'DNI debe tener 8 dígitos'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el DNI ya existe
        cursor.execute("SELECT * FROM trabajadores WHERE dni = ?", (dni,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'mensaje': 'El DNI ya está registrado'})
        
        # Insertar nuevo trabajador
        cursor.execute('''
            INSERT INTO trabajadores (dni, nombre, cargo, area, fecha_ingreso, sueldo_base)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (dni, nombre, cargo, area, fecha_ingreso, sueldo_base))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Trabajador agregado correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'mensaje': f'Error: {str(e)}'})

@app.route('/admin/eliminar-trabajador', methods=['POST'])
def admin_eliminar_trabajador():
    """Eliminar trabajador Y TODOS SUS REGISTROS automáticamente - VERSIÓN ROBUSTA"""
    try:
        data = request.get_json()
        dni = data.get('dni')
        
        print(f"🗑️  SOLICITUD ELIMINAR TRABAJADOR: DNI={dni}")
        
        # Validación estricta
        if not dni or len(str(dni).strip()) != 8:
            return jsonify({
                'success': False, 
                'mensaje': 'DNI inválido o faltante'
            })
        
        dni = str(dni).strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. VERIFICAR QUE EL TRABAJADOR EXISTE
        cursor.execute("SELECT nombre FROM trabajadores WHERE dni = ?", (dni,))
        trabajador = cursor.fetchone()
        
        if not trabajador:
            conn.close()
            return jsonify({
                'success': False, 
                'mensaje': 'Trabajador no encontrado'
            })
        
        nombre_trabajador = trabajador['nombre']
        print(f"✅ Trabajador encontrado: {nombre_trabajador}")
        
        # 2. ELIMINAR TODAS LAS ASISTENCIAS DEL TRABAJADOR (PRIMERO)
        cursor.execute("SELECT COUNT(*) FROM asistencias WHERE dni = ?", (dni,))
        total_asistencias = cursor.fetchone()[0]
        
        if total_asistencias > 0:
            cursor.execute("DELETE FROM asistencias WHERE dni = ?", (dni,))
            asistencias_eliminadas = cursor.rowcount
            print(f"🗑️  Eliminadas {asistencias_eliminadas} asistencias")
        else:
            asistencias_eliminadas = 0
            print("ℹ️  No había asistencias para eliminar")
        
        # 3. ELIMINAR ARCHIVOS OFFLINE DEL TRABAJADOR
        archivos_offline_eliminados = eliminar_archivos_offline_trabajador(dni)
        
        # 4. FINALMENTE ELIMINAR EL TRABAJADOR
        cursor.execute("DELETE FROM trabajadores WHERE dni = ?", (dni,))
        
        # 5. CONFIRMAR CAMBIOS
        conn.commit()
        conn.close()
        
        print(f"✅ ELIMINACIÓN COMPLETADA: {nombre_trabajador}")
        
        return jsonify({
            'success': True, 
            'mensaje': f'Trabajador {nombre_trabajador} eliminado correctamente',
            'detalles': {
                'asistencias_eliminadas': asistencias_eliminadas,
                'archivos_offline_eliminados': archivos_offline_eliminados,
                'trabajador': nombre_trabajador
            }
        })
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO eliminando trabajador: {str(e)}")
        # Asegurarse de cerrar la conexión en caso de error
        try:
            conn.close()
        except:
            pass
            
        return jsonify({
            'success': False, 
            'mensaje': f'Error del sistema: {str(e)}'
        })

def eliminar_archivos_offline_trabajador(dni):
    """Elimina archivos offline de un trabajador específico - FUNCIÓN AUXILIAR"""
    try:
        archivos_eliminados = 0
        offline_dir = 'data_offline'
        
        # Verificar si existe el directorio
        if not os.path.exists(offline_dir):
            return 0
        
        # Buscar y eliminar archivos del DNI específico
        patron_archivo = f"{dni}_pendientes.json"
        archivo_path = os.path.join(offline_dir, patron_archivo)
        
        if os.path.exists(archivo_path):
            os.remove(archivo_path)
            archivos_eliminados += 1
            print(f"🗑️  Eliminado archivo offline: {patron_archivo}")
        
        # También verificar en registros con error
        archivo_errores = os.path.join(offline_dir, 'registros_con_error.json')
        if os.path.exists(archivo_errores):
            try:
                with open(archivo_errores, 'r', encoding='utf-8') as f:
                    registros = json.load(f)
                
                # Filtrar registros que NO sean del DNI a eliminar
                registros_filtrados = [r for r in registros if r.get('dni') != dni]
                
                # Si se eliminaron registros, guardar el archivo actualizado
                if len(registros_filtrados) != len(registros):
                    with open(archivo_errores, 'w', encoding='utf-8') as f:
                        json.dump(registros_filtrados, f, ensure_ascii=False, indent=2)
                    
                    eliminados = len(registros) - len(registros_filtrados)
                    archivos_eliminados += eliminados
                    print(f"🗑️  Eliminados {eliminados} registros del archivo de errores")
                    
            except Exception as e:
                print(f"⚠️  Error procesando archivo de errores: {e}")
        
        return archivos_eliminados
        
    except Exception as e:
        print(f"⚠️  Error eliminando archivos offline: {e}")
        return 0

# ================= RUTAS DE EDICIÓN MANUAL =================

@app.route('/admin/asistencia-detalle')
def admin_asistencia_detalle():
    """Obtener detalle de una asistencia específica"""
    dni = request.args.get('dni')
    fecha = request.args.get('fecha')
    
    if not dni or not fecha:
        return jsonify({'error': 'DNI y fecha requeridos'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM asistencias 
        WHERE dni = ? AND fecha = ?
    ''', (dni, fecha))
    
    asistencia = cursor.fetchone()
    conn.close()
    
    if asistencia:
        return jsonify(dict(asistencia))
    else:
        return jsonify({'entrada': None, 'salida': None, 'observaciones': None})

@app.route('/admin/editar-asistencia', methods=['POST'])
def admin_editar_asistencia():
    """Editar o crear una asistencia manualmente"""
    try:
        data = request.get_json()
        dni = data.get('dni')
        fecha = data.get('fecha')
        entrada = data.get('entrada')
        salida = data.get('salida')
        observaciones = data.get('observaciones', '')
        
        if not dni or not fecha:
            return jsonify({'success': False, 'mensaje': 'DNI y fecha requeridos'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM asistencias WHERE dni = ? AND fecha = ?",
            (dni, fecha)
        )
        existe = cursor.fetchone()
        
        horas_trabajadas = 0
        horas_extras = 0
        estado = 'PENDIENTE'
        
        if entrada and salida:
            try:
                entrada_dt = datetime.strptime(entrada, '%H:%M').time()
                salida_dt = datetime.strptime(salida, '%H:%M').time()
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
                
                entrada_completa = datetime.combine(fecha_dt, entrada_dt)
                salida_completa = datetime.combine(fecha_dt, salida_dt)
                
                if salida_completa < entrada_completa:
                    salida_completa += timedelta(days=1)
                
                horas_trabajadas = (salida_completa - entrada_completa).total_seconds() / 3600
                horas_extras = max(0, horas_trabajadas - HORAS_JORNADA_NORMAL)
                estado = determinar_estado(entrada + ':00')  # Agregar segundos
                
            except ValueError as e:
                print(f"Error calculando horas: {e}")
        
        elif entrada and not salida:
            estado = determinar_estado(entrada + ':00')
        elif not entrada and not salida:
            estado = 'FALTA'
        
        if existe:
            cursor.execute('''
                UPDATE asistencias 
                SET entrada = ?, salida = ?, horas_trabajadas = ?, horas_extras = ?, 
                    estado = ?, observaciones = ?, tipo_registro = 'MANUAL'
                WHERE dni = ? AND fecha = ?
            ''', (entrada, salida, round(horas_trabajadas, 2), round(horas_extras, 2), 
                  estado, observaciones, dni, fecha))
        else:
            cursor.execute('''
                INSERT INTO asistencias 
                (dni, fecha, entrada, salida, horas_trabajadas, horas_extras, estado, observaciones, tipo_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'MANUAL')
            ''', (dni, fecha, entrada, salida, round(horas_trabajadas, 2), 
                  round(horas_extras, 2), estado, observaciones))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Asistencia guardada correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'mensaje': f'Error: {str(e)}'})

@app.route('/admin/justificar-falta', methods=['POST'])
def admin_justificar_falta():
    """Justificar una falta o tardanza - CORREGIDO"""
    try:
        data = request.get_json()
        dni = data.get('dni')
        fecha = data.get('fecha')
        motivo = data.get('motivo')
        descripcion = data.get('descripcion', '')
        
        if not dni or not fecha:
            return jsonify({'success': False, 'mensaje': 'DNI y fecha requeridos'})
        
        observaciones = f"JUSTIFICADO - Motivo: {motivo}"
        if descripcion:
            observaciones += f" - {descripcion}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM asistencias WHERE dni = ? AND fecha = ?",
            (dni, fecha)
        )
        existe = cursor.fetchone()
        
        if existe:
            # ACTUALIZAR ESTADO A 'JUSTIFICADO' - ESTA ES LA CORRECCIÓN
            cursor.execute('''
                UPDATE asistencias 
                SET estado = 'JUSTIFICADO', observaciones = ?, tipo_registro = 'JUSTIFICADO'
                WHERE dni = ? AND fecha = ?
            ''', (observaciones, dni, fecha))
        else:
            cursor.execute('''
                INSERT INTO asistencias 
                (dni, fecha, estado, observaciones, tipo_registro)
                VALUES (?, ?, 'JUSTIFICADO', ?, 'JUSTIFICADO')
            ''', (dni, fecha, observaciones))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Falta justificada correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'mensaje': f'Error: {str(e)}'})

@app.route('/admin/eliminar-asistencia', methods=['POST'])
def admin_eliminar_asistencia():
    """Eliminar una asistencia"""
    try:
        data = request.get_json()
        dni = data.get('dni')
        fecha = data.get('fecha')
        
        if not dni or not fecha:
            return jsonify({'success': False, 'mensaje': 'DNI y fecha requeridos'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM asistencias WHERE dni = ? AND fecha = ?",
            (dni, fecha)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Asistencia eliminada correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'mensaje': f'Error: {str(e)}'})

# ================= RUTAS DE REPORTES CORREGIDAS =================

@app.route('/admin/generar-reporte', methods=['POST'])
def admin_generar_reporte():
    """Generar reporte mensual para un trabajador - CORREGIDO"""
    try:
        data = request.get_json()
        print(f"📊 SOLICITUD REPORTE: {data}")
        
        dni = data.get('dni', '').strip()
        mes = data.get('mes')
        anio = data.get('anio')
        
        if not mes or not anio:
            return jsonify({'success': False, 'mensaje': 'Mes y año requeridos'})
        
        # Si no se selecciona trabajador, usar el primero disponible
        if not dni:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT dni FROM trabajadores LIMIT 1")
            trabajador = cursor.fetchone()
            conn.close()
            
            if trabajador:
                dni = trabajador['dni']
            else:
                return jsonify({'success': False, 'mensaje': 'No hay trabajadores registrados'})
        
        print(f"📊 Generando reporte para DNI: {dni}, Mes: {mes}, Año: {anio}")
        
        resumen = obtener_resumen_mensual(dni, int(mes), int(anio))
        
        if not resumen:
            return jsonify({'success': False, 'mensaje': 'No se encontraron datos para el reporte'})
        
        print(f"✅ Reporte generado exitosamente")
        return jsonify({
            'success': True, 
            'reporte': resumen
        })
        
    except Exception as e:
        print(f"❌ ERROR generando reporte: {str(e)}")
        return jsonify({'success': False, 'mensaje': f'Error generando reporte: {str(e)}'})

@app.route('/admin/generar-reporte-completo', methods=['POST'])
def admin_generar_reporte_completo():
    """Generar reporte mensual para TODOS los trabajadores - NUEVO"""
    try:
        data = request.get_json()
        print(f"📊 SOLICITUD REPORTE COMPLETO: {data}")
        
        mes = data.get('mes')
        anio = data.get('anio')
        
        if not mes or not anio:
            return jsonify({'success': False, 'mensaje': 'Mes y año requeridos'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los trabajadores activos
        cursor.execute("SELECT dni FROM trabajadores WHERE activo = TRUE")
        trabajadores = cursor.fetchall()
        
        if not trabajadores:
            conn.close()
            return jsonify({'success': False, 'mensaje': 'No hay trabajadores registrados'})
        
        reportes_individuales = []
        totales_generales = {
            'total_trabajadores': 0,
            'total_dias_trabajados': 0,
            'total_faltas': 0,
            'total_tardanzas': 0,
            'total_horas_extras': 0,
            'total_pago_extras': 0
        }
        
        for trab in trabajadores:
            dni = trab['dni']
            resumen = obtener_resumen_mensual(dni, int(mes), int(anio))
            
            if resumen:
                reportes_individuales.append(resumen)
                totales_generales['total_trabajadores'] += 1
                totales_generales['total_dias_trabajados'] += resumen['estadisticas']['dias_trabajados']
                totales_generales['total_faltas'] += resumen['estadisticas']['faltas']
                totales_generales['total_tardanzas'] += resumen['estadisticas']['tardanzas']
                totales_generales['total_horas_extras'] += resumen['estadisticas']['total_horas_extras']
                totales_generales['total_pago_extras'] += resumen['pago_horas_extras']['total_pagar']
        
        conn.close()
        
        print(f"✅ Reporte completo generado para {len(reportes_individuales)} trabajadores")
        
        return jsonify({
            'success': True, 
            'tipo': 'completo',
            'reportes': reportes_individuales,
            'totales': totales_generales,
            'mes': mes,
            'anio': anio
        })
        
    except Exception as e:
        print(f"❌ ERROR generando reporte completo: {str(e)}")
        return jsonify({'success': False, 'mensaje': f'Error generando reporte completo: {str(e)}'})

@app.route('/reporte-imprimir')
def reporte_imprimir():
    """Página para imprimir el reporte - COMPLETAMENTE FUNCIONAL"""
    try:
        dni = request.args.get('dni', '')
        mes = request.args.get('mes', '')
        anio = request.args.get('anio', '')
        
        print(f"🖨️ Solicitando reporte imprimir: DNI={dni}, Mes={mes}, Año={anio}")
        
        if not dni or not mes or not anio:
            return "Error: Parámetros incompletos", 400
        
        # OBTENER LOS DATOS REALES DEL REPORTE
        resumen = obtener_resumen_mensual(dni, int(mes), int(anio))
        
        if not resumen:
            return "No se encontraron datos para el reporte", 404
            
        print(f"✅ Datos del reporte obtenidos, enviando a template...")
        
        # Pasar los datos COMPLETOS al template
        return render_template('reporte_imprimir.html', 
                             reporte=resumen,
                             mes=mes, 
                             anio=anio,
                             trabajador=resumen['trabajador'],
                             estadisticas=resumen['estadisticas'],
                             pago=resumen['pago_horas_extras'],
                             detalle=resumen['detalle_diario'])
        
    except Exception as e:
        print(f"❌ ERROR en reporte-imprimir: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/admin/descargar-excel')
def admin_descargar_excel():
    """Descargar reporte en Excel - CORREGIDO"""
    try:
        dni = request.args.get('dni', '')
        mes = request.args.get('mes', '')
        anio = request.args.get('anio', '')
        
        print(f"📥 Solicitando Excel: DNI={dni}, Mes={mes}, Año={anio}")
        
        if not dni or not mes or not anio:
            return "Error: Parámetros requeridos", 400
        
        # Verificar que el trabajador existe
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM trabajadores WHERE dni = ?", (dni,))
        trabajador = cursor.fetchone()
        conn.close()
        
        if not trabajador:
            return "Trabajador no encontrado", 404
        
        resumen = obtener_resumen_mensual(dni, int(mes), int(anio))
        
        if not resumen:
            return "No se encontraron datos", 404
        
        try:
            import pandas as pd
            from io import BytesIO
            
            # Crear datos para Excel
            datos_excel = []
            for dia in resumen['detalle_diario']:
                datos_excel.append({
                    'Fecha': dia['fecha'],
                    'Entrada': dia['entrada'] or '--:--:--',
                    'Salida': dia['salida'] or '--:--:--',
                    'Horas Trabajadas': dia['horas_trabajadas'] or 0,
                    'Horas Extras': dia['horas_extras'] or 0,
                    'Estado': dia['estado'] or 'NO REGISTRADO',
                    'Observaciones': dia['observaciones'] or ''
                })
            
            df_detalle = pd.DataFrame(datos_excel)
            
            # Crear resumen
            datos_resumen = {
                'Concepto': [
                    'Nombre', 'DNI', 'Cargo', 'Sueldo Base',
                    'Días Trabajados', 'Faltas', 'Tardanzas',
                    'Horas Extras Totales', 'Pago por Hora Extra', 'Total a Pagar'
                ],
                'Valor': [
                    resumen['trabajador']['nombre'],
                    resumen['trabajador']['dni'],
                    resumen['trabajador']['cargo'],
                    f"S/ {resumen['trabajador']['sueldo_base']}",
                    resumen['estadisticas']['dias_trabajados'],
                    resumen['estadisticas']['faltas'],
                    resumen['estadisticas']['tardanzas'],
                    f"{resumen['estadisticas']['total_horas_extras']:.2f} horas",
                    f"S/ {resumen['pago_horas_extras']['pago_por_hora']:.2f}",
                    f"S/ {resumen['pago_horas_extras']['total_pagar']:.2f}"
                ]
            }
            df_resumen = pd.DataFrame(datos_resumen)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_detalle.to_excel(writer, sheet_name='Asistencias', index=False)
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            
            output.seek(0)
            
            nombre_archivo = f"reporte_{dni}_{mes}_{anio}.xlsx"
            
            print(f"✅ Excel generado exitosamente: {nombre_archivo}")
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nombre_archivo
            )
            
        except ImportError:
            return jsonify({'success': False, 'mensaje': 'Pandas no está instalado'})
            
    except Exception as e:
        print(f"❌ ERROR generando Excel: {str(e)}")
        return f"Error generando Excel: {str(e)}", 500
    
# ================= GESTIÓN HISTÓRICA =================

@app.route('/admin/asistencias-historicas')
def admin_asistencias_historicas():
    """Obtener asistencias históricas con filtros - NUEVO"""
    try:
        trabajador_dni = request.args.get('trabajador', '')
        mes = request.args.get('mes', '')
        anio = request.args.get('anio', '')
        estado = request.args.get('estado', '')
        pagina = int(request.args.get('pagina', 1))
        por_pagina = int(request.args.get('por_pagina', 50))
        
        print(f"📅 Solicitando asistencias históricas: DNI={trabajador_dni}, Mes={mes}, Año={anio}, Estado={estado}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir query con filtros
        query = '''
            SELECT a.*, t.nombre, t.cargo 
            FROM asistencias a
            JOIN trabajadores t ON a.dni = t.dni
            WHERE 1=1
        '''
        params = []
        
        if trabajador_dni:
            query += ' AND a.dni = ?'
            params.append(trabajador_dni)
        
        if mes:
            query += ' AND strftime("%m", a.fecha) = ?'
            params.append(mes.zfill(2))
        
        if anio:
            query += ' AND strftime("%Y", a.fecha) = ?'
            params.append(anio)
        
        if estado:
            query += ' AND a.estado = ?'
            params.append(estado)
        
        # Ordenar por fecha más reciente primero
        query += ' ORDER BY a.fecha DESC, t.nombre'
        
        # Paginación
        offset = (pagina - 1) * por_pagina
        query += ' LIMIT ? OFFSET ?'
        params.extend([por_pagina, offset])
        
        cursor.execute(query, params)
        asistencias = []
        for row in cursor.fetchall():
            asistencias.append(dict(row))
        
        # Contar total para paginación
        count_query = '''
            SELECT COUNT(*) as total 
            FROM asistencias a
            JOIN trabajadores t ON a.dni = t.dni
            WHERE 1=1
        '''
        count_params = []
        
        if trabajador_dni:
            count_query += ' AND a.dni = ?'
            count_params.append(trabajador_dni)
        
        if mes:
            count_query += ' AND strftime("%m", a.fecha) = ?'
            count_params.append(mes.zfill(2))
        
        if anio:
            count_query += ' AND strftime("%Y", a.fecha) = ?'
            count_params.append(anio)
        
        if estado:
            count_query += ' AND a.estado = ?'
            count_params.append(estado)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'asistencias': asistencias,
            'total': total,
            'pagina': pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina
        })
        
    except Exception as e:
        print(f"❌ ERROR obteniendo asistencias históricas: {str(e)}")
        return jsonify({'success': False, 'mensaje': f'Error: {str(e)}'})

@app.route('/admin/compensar-falta', methods=['POST'])
def admin_compensar_falta():
    """Compensar una falta trabajando otro día - NUEVO"""
    try:
        data = request.get_json()
        dni = data.get('dni')
        fecha_falta = data.get('fecha_falta')
        fecha_compensacion = data.get('fecha_compensacion')
        horas_compensadas = data.get('horas_compensadas', 8)
        observaciones = data.get('observaciones', '')
        
        if not dni or not fecha_falta or not fecha_compensacion:
            return jsonify({'success': False, 'mensaje': 'Datos incompletos'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Marcar la falta como COMPENSADA
        cursor.execute('''
            UPDATE asistencias 
            SET estado = 'COMPENSADO', observaciones = ?
            WHERE dni = ? AND fecha = ?
        ''', (f"FALTA COMPENSADA - {observaciones}", dni, fecha_falta))
        
        # 2. Crear o actualizar el día de compensación
        cursor.execute('''
            INSERT OR REPLACE INTO asistencias 
            (dni, fecha, entrada, salida, horas_trabajadas, horas_extras, estado, observaciones, tipo_registro)
            VALUES (?, ?, '08:00', '17:00', ?, 0, 'COMPENSADO', ?, 'COMPENSACION')
        ''', (dni, fecha_compensacion, horas_compensadas, f"COMPENSACIÓN por falta del {fecha_falta} - {observaciones}"))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Falta compensada correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'mensaje': f'Error: {str(e)}'})

@app.route('/admin/exportar-historico-excel')
def admin_exportar_historico_excel():
    """Exportar historico completo a Excel - NUEVO"""
    try:
        import pandas as pd
        from io import BytesIO
        from datetime import datetime
        
        trabajador_dni = request.args.get('trabajador', '')
        mes = request.args.get('mes', '')
        anio = request.args.get('anio', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir query con filtros
        query = '''
            SELECT a.dni, t.nombre, t.cargo, a.fecha, a.entrada, a.salida, 
                   a.horas_trabajadas, a.horas_extras, a.estado, a.observaciones, a.tipo_registro
            FROM asistencias a
            JOIN trabajadores t ON a.dni = t.dni
            WHERE 1=1
        '''
        params = []
        
        if trabajador_dni:
            query += ' AND a.dni = ?'
            params.append(trabajador_dni)
        
        if mes:
            query += ' AND strftime("%m", a.fecha) = ?'
            params.append(mes.zfill(2))
        
        if anio:
            query += ' AND strftime("%Y", a.fecha) = ?'
            params.append(anio)
        
        query += ' ORDER BY a.fecha DESC, t.nombre'
        
        cursor.execute(query, params)
        
        datos_excel = []
        for row in cursor.fetchall():
            datos_excel.append(dict(row))
        
        conn.close()
        
        df = pd.DataFrame(datos_excel)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Asistencias Historicas', index=False)
        
        output.seek(0)
        
        nombre_archivo = f"historico_asistencias_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        return jsonify({'success': False, 'mensaje': f'Error exportando: {str(e)}'})
    
@app.route('/admin/limpiar-registros-huérfanos', methods=['POST'])
def limpiar_registros_huérfanos():
    """Limpia TODOS los registros huérfanos del sistema - FUNCIÓN DE MANTENIMIENTO"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Contar registros antes
        cursor.execute("SELECT COUNT(*) FROM asistencias")
        total_antes = cursor.fetchone()[0]
        
        # 2. Encontrar DNIs huérfanos
        cursor.execute('''
            SELECT DISTINCT dni FROM asistencias 
            WHERE dni NOT IN (SELECT dni FROM trabajadores)
        ''')
        dnis_huérfanos = [row[0] for row in cursor.fetchall()]
        
        # 3. Eliminar registros huérfanos
        cursor.execute('''
            DELETE FROM asistencias 
            WHERE dni NOT IN (SELECT dni FROM trabajadores)
        ''')
        
        registros_eliminados = cursor.rowcount
        
        # 4. Contar después
        cursor.execute("SELECT COUNT(*) FROM asistencias")
        total_despues = cursor.fetchone()[0]
        
        # 5. Limpiar archivos offline huérfanos
        archivos_eliminados = limpiar_archivos_offline_huérfanos()
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'mensaje': f'Limpieza completada exitosamente',
            'detalles': {
                'registros_eliminados': registros_eliminados,
                'dnis_huérfanos_encontrados': dnis_huérfanos,
                'archivos_offline_eliminados': archivos_eliminados,
                'total_antes': total_antes,
                'total_despues': total_despues
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'mensaje': f'Error en limpieza: {str(e)}'
        })

def limpiar_archivos_offline_huérfanos():
    """Limpia archivos offline de trabajadores que no existen"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener DNIs válidos
        cursor.execute("SELECT dni FROM trabajadores")
        dnis_validos = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        
        archivos_eliminados = 0
        offline_dir = 'data_offline'
        
        if not os.path.exists(offline_dir):
            return 0
        
        # Limpiar archivos _pendientes.json
        for archivo in os.listdir(offline_dir):
            if archivo.endswith('_pendientes.json'):
                dni_archivo = archivo.replace('_pendientes.json', '')
                
                if dni_archivo not in dnis_validos:
                    archivo_path = os.path.join(offline_dir, archivo)
                    os.remove(archivo_path)
                    archivos_eliminados += 1
                    print(f"🗑️  Eliminado archivo huérfano: {archivo}")
        
        return archivos_eliminados
        
    except Exception as e:
        print(f"⚠️  Error limpiando archivos offline huérfanos: {e}")
        return 0

# Inicializar base de datos al empezar
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001, host='0.0.0.0')