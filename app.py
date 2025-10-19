from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import sqlite3
import os
from datetime import datetime
from database import get_db_connection, init_db, migrar_datos_json, sincronizar_sqlite_a_json, restaurar_desde_json

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura_admin_12345'

# ================= INICIALIZACIÓN MEJORADA PARA RENDER =================
def initialize_database():
    """Inicializa la base de datos de forma SEGURA para Render"""
    print("🔄 Inicializando base de datos...")
    
    # 1. Siempre crear tablas si no existen
    init_db()
    
    # 2. Estrategia diferente para Render vs Desarrollo
    if os.environ.get('RENDER'):
        print("🏗️  Entorno RENDER detectado - Verificando datos...")
        
        # Verificar si la base de datos SQLite tiene datos REALES (más que solo el admin)
        conn = get_db_connection()
        result = conn.execute('SELECT COUNT(*) as count FROM vendedores').fetchone()
        # Manejar tanto PostgreSQL (tupla) como SQLite (dict)
        vendedores_count = result[0] if isinstance(result, tuple) else result['count']
        
        # Verificar si solo existe el admin por defecto
        solo_admin = False
        if vendedores_count == 1:
            admin = conn.execute("SELECT * FROM vendedores WHERE codigo = 'DARKEYES'").fetchone()
            if admin:
                solo_admin = True
        
        conn.close()
        
        if vendedores_count == 0 or solo_admin:
            print("📦 SQLite vacío o solo con admin - Restaurando desde respaldo...")
            if restaurar_desde_json():
                print("✅ Datos restaurados desde respaldo JSON")
            else:
                print("🆕 No hay respaldo válido, iniciando con datos básicos...")
                # Solo crear admin si no existe
                conn = get_db_connection()
                cursor = conn.execute('SELECT COUNT(*) as count FROM vendedores WHERE codigo = 'DARKEYES'')
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
                
                # CREAR RESPALDO INICIAL SIEMPRE
                print("📝 Creando respaldo inicial...")
                sincronizar_sqlite_a_json()
        else:
            print(f"✅ SQLite ya tiene {vendedores_count} vendedores - Todo listo")
            
            # ACTUALIZAR RESPALDO por si acaso
            sincronizar_sqlite_a_json()
            
    else:
        # Entorno desarrollo: migrar normalmente
        print("💻 Entorno DESARROLLO - Migrando datos...")
        migrar_datos_json()
        # Crear respaldo inicial en desarrollo también
        sincronizar_sqlite_a_json()
    
    print("✅ Base de datos inicializada correctamente")

# Ejecutar inicialización al importar el módulo
initialize_database()

# ================= CONFIGURACIÓN PARA DOMINIO PERSONALIZADO =================
@app.before_request
def before_request():
    """Configura el dominio correcto para todas las URLs generadas"""
    # Si estamos en producción (Render) y el dominio es personalizado
    if request.host == 'mimunditoweb.net.pe':
        # Asegurar que url_for genere URLs con el dominio correcto
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        app.config['SERVER_NAME'] = 'mimunditoweb.net.pe'

# ================= RUTAS PARA SERVIR ASSETS Y DATA =================
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Sirve archivos desde la carpeta assets/"""
    return send_from_directory('assets', filename)

@app.route('/data/<path:filename>')  
def serve_data(filename):
    """Sirve archivos desde la carpeta data/"""
    return send_from_directory('data', filename)

@app.route('/img/<path:filename>')
def serve_img(filename):
    """Sirve archivos de imagen desde la carpeta img/ en la raíz"""
    return send_from_directory('img', filename)

# ================= FUNCIONES AUXILIARES CON SQLite =================

def cargar_vendedores():
    """Carga todos los vendedores desde SQLite"""
    conn = get_db_connection()
    vendedores = conn.execute('SELECT * FROM vendedores').fetchall()
    conn.close()
    return {v['codigo']: dict(v) for v in vendedores}

def obtener_vendedor(codigo):
    """Obtiene un vendedor específico"""
    conn = get_db_connection()
    vendedor = conn.execute('SELECT * FROM vendedores WHERE codigo = ?', (codigo,)).fetchone()
    conn.close()
    return dict(vendedor) if vendedor else None

def actualizar_vendedor(codigo, datos):
    """Actualiza los datos de un vendedor"""
    conn = get_db_connection()
    conn.execute('''
        UPDATE vendedores 
        SET nombre = ?, device_id = ?, activo = ?, es_admin = ?, ultimo_acceso = ?, accesos_totales = ?
        WHERE codigo = ?
    ''', (
        datos['nombre'],
        datos.get('device_id', ''),
        datos.get('activo', True),
        datos.get('es_admin', False),
        datos.get('ultimo_acceso'),
        datos.get('accesos_totales', 0),
        codigo
    ))
    conn.commit()
    conn.close()

def crear_vendedor(codigo, datos):
    """Crea un nuevo vendedor"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO vendedores 
        (codigo, nombre, device_id, activo, es_admin, fecha_creacion, accesos_totales)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        codigo,
        datos['nombre'],
        datos.get('device_id', ''),
        datos.get('activo', True),
        datos.get('es_admin', False),
        datetime.now().isoformat(),
        datos.get('accesos_totales', 0)
    ))
    conn.commit()
    conn.close()

def eliminar_vendedor_db(codigo):
    """Elimina un vendedor de la base de datos"""
    conn = get_db_connection()
    conn.execute('DELETE FROM vendedores WHERE codigo = ?', (codigo,))
    conn.commit()
    conn.close()

def registrar_acceso_db(vendedor_id, dispositivo, exitoso, ip):
    """Registra un intento de acceso en la base de datos"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO accesos (vendedor_id, dispositivo, exitoso, ip)
        VALUES (?, ?, ?, ?)
    ''', (vendedor_id, dispositivo, exitoso, ip))
    conn.commit()
    conn.close()

def registrar_sesion(vendedor_id, dispositivo, ip):
    """Registra una nueva sesión activa"""
    sesion_id = f"{vendedor_id}_{dispositivo}_{datetime.now().timestamp()}"
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO sesiones_activas (sesion_id, vendedor_id, dispositivo, ip)
        VALUES (?, ?, ?, ?)
    ''', (sesion_id, vendedor_id, dispositivo, ip))
    conn.commit()
    conn.close()
    return sesion_id

def invalidar_sesiones_vendedor(vendedor_id):
    """Invalida TODAS las sesiones de un vendedor"""
    conn = get_db_connection()
    cursor = conn.execute(
        'UPDATE sesiones_activas SET activa = FALSE, fecha_fin = ? WHERE vendedor_id = ? AND activa = TRUE',
        (datetime.now().isoformat(), vendedor_id)
    )
    sesiones_invalidadas = cursor.rowcount
    conn.commit()
    conn.close()
    return sesiones_invalidadas

def sesion_es_valida(vendedor_id, dispositivo_actual, vendedor_device_id):
    """Verifica si la sesión actual es válida"""
    conn = get_db_connection()
    
    # Usar dispositivo_actual si el vendedor no tiene Device ID configurado
    dispositivo_buscar = vendedor_device_id if vendedor_device_id else dispositivo_actual
    
    sesion = conn.execute(
        'SELECT * FROM sesiones_activas WHERE vendedor_id = ? AND dispositivo = ? AND activa = TRUE',
        (vendedor_id, dispositivo_buscar)
    ).fetchone()
    
    conn.close()
    return sesion is not None

def vendedor_autenticado():
    """Verifica si el usuario está autenticado Y tiene sesión válida"""
    if 'vendedor_id' not in session:
        return False
    
    vendedor_id = session.get('vendedor_id')
    dispositivo_actual = session.get('dispositivo_actual', '')
    vendedor_device_id = session.get('vendedor_device_id', '')
    
    # Verificar si es administrador
    vendedor = obtener_vendedor(vendedor_id)
    if not vendedor:
        return False
    
    # Si es administrador, bypass de seguridad
    if vendedor.get('es_admin', False):
        return True
    
    # Verificar si la sesión sigue siendo válida para usuarios normales
    return sesion_es_valida(vendedor_id, dispositivo_actual, vendedor_device_id)

def es_administrador():
    """Verifica si el usuario es administrador"""
    vendedor_id = session.get('vendedor_id')
    if not vendedor_id:
        return False
    
    vendedor = obtener_vendedor(vendedor_id)
    return vendedor.get('es_admin', False) if vendedor else False

def registrar_acceso(vendedor_id, dispositivo, exitoso):
    """Registra un intento de acceso"""
    registrar_acceso_db(vendedor_id, dispositivo, exitoso, request.remote_addr)

# ================= RUTAS PÚBLICAS =================

@app.route('/')
def login():
    """Página de login"""
    if vendedor_autenticado():
        return redirect(url_for('distrimundoescolar'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def autenticar():
    """Procesa el login del vendedor"""
    codigo = request.form.get('codigo', '').strip().upper()
    dispositivo = request.form.get('dispositivo', '').strip()
    
    vendedor = obtener_vendedor(codigo)
    
    if vendedor:
        # Verificar si está activo
        if not vendedor.get('activo', True):
            registrar_acceso(codigo, dispositivo, False)
            return render_template('login.html', 
                                error="❌ Cuenta desactivada. Contacta al administrador.")
        
        # Verificar Device ID (solo si está configurado y no está vacío)
        if vendedor.get('device_id') and vendedor['device_id'].strip():
            if vendedor['device_id'] != dispositivo:
                registrar_acceso(codigo, dispositivo, False)
                return render_template('login.html', 
                                    error="❌ Dispositivo no autorizado. Contacta al administrador.")
        
        # Login exitoso
        session['vendedor_id'] = codigo
        session['vendedor_nombre'] = vendedor['nombre']
        session['vendedor_device_id'] = vendedor.get('device_id', '')
        session['dispositivo_actual'] = dispositivo
        session['es_admin'] = vendedor.get('es_admin', False)
        
        # Registrar sesión activa
        registrar_sesion(codigo, dispositivo, request.remote_addr)
        
        # Actualizar último acceso
        vendedor['ultimo_acceso'] = datetime.now().isoformat()
        vendedor['accesos_totales'] = vendedor.get('accesos_totales', 0) + 1
        actualizar_vendedor(codigo, vendedor)
        
        # Registrar acceso exitoso
        registrar_acceso(codigo, dispositivo, True)
        
        if vendedor.get('es_admin', False):
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('distrimundoescolar'))
    else:
        registrar_acceso(codigo, dispositivo, False)
        return render_template('login.html', 
                            error="❌ Código inválido o cuenta desactivada")

# ================= RUTAS PROTEGIDAS =================

@app.route('/distrimundoescolar')
def distrimundoescolar():
    """Página principal después del login"""
    if not vendedor_autenticado():
        return redirect(url_for('login'))
    return render_template('distrimundoescolar.html')

@app.route('/promociones')
def promociones():
    """Página de promociones"""
    if not vendedor_autenticado():
        return redirect(url_for('login'))
    return render_template('promociones.html')

@app.route('/nosotros')
def nosotros():
    """Página nosotros"""
    if not vendedor_autenticado():
        return redirect(url_for('login'))
    return render_template('nosotros.html')

@app.route('/contacto')
def contacto():
    """Página contacto"""
    if not vendedor_autenticado():
        return redirect(url_for('login'))
    return render_template('contacto.html')

# ================= PANEL ADMINISTRADOR =================

@app.route('/admin')
def admin_panel():
    """Panel de administración"""
    if not vendedor_autenticado() or not es_administrador():
        return redirect(url_for('login'))
    return render_template('admin_panel.html')

@app.route('/admin/agregar-vendedor', methods=['POST'])
def agregar_vendedor():
    """Agrega un nuevo vendedor"""
    if not vendedor_autenticado() or not es_administrador():
        return jsonify({'error': 'No autorizado'}), 403
    
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    device_id = request.form.get('device_id', '').strip()
    
    if not codigo or not nombre:
        return jsonify({'error': 'Código y nombre son requeridos'}), 400
    
    vendedor_existente = obtener_vendedor(codigo)
    if vendedor_existente:
        return jsonify({'error': 'El código ya existe'}), 400
    
    try:
        crear_vendedor(codigo, {
            'nombre': nombre,
            'device_id': device_id,
            'activo': True,
            'es_admin': False
        })
        
        # ✅ CRÍTICO: Sincronizar inmediatamente después de agregar
        sincronizar_sqlite_a_json()
        
        return jsonify({
            'success': True,
            'mensaje': f'Vendedor {nombre} agregado exitosamente',
            'codigo': codigo
        })
    except Exception as e:
        return jsonify({'error': f'Error guardando el vendedor: {str(e)}'}), 500

@app.route('/admin/editar-vendedor/<codigo_actual>', methods=['POST'])
def editar_vendedor(codigo_actual):
    """Edita un vendedor existente - CON CAMBIO DE CÓDIGO"""
    if not vendedor_autenticado() or not es_administrador():
        return jsonify({'error': 'No autorizado'}), 403
    
    vendedor_actual = obtener_vendedor(codigo_actual)
    if not vendedor_actual:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    # Obtener nuevos datos del formulario
    nuevo_codigo = request.form.get('nuevo_codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    device_id = request.form.get('device_id', '').strip()
    activo = request.form.get('activo') == 'on'
    es_admin = request.form.get('es_admin') == 'on'
    
    print(f"📝 Editando: {codigo_actual} -> {nuevo_codigo}")
    print(f"📝 Datos: nombre={nombre}, activo={activo}, es_admin={es_admin}")
    
    # Validar que el nuevo código no esté en uso (excepto si es el mismo)
    if nuevo_codigo != codigo_actual and obtener_vendedor(nuevo_codigo):
        return jsonify({'error': 'El nuevo código ya está en uso'}), 400
    
    if not nuevo_codigo:
        return jsonify({'error': 'El código no puede estar vacío'}), 400
    
    estado_anterior = vendedor_actual.get('activo', True)
    usuario_actual_editado = (session.get('vendedor_id') == codigo_actual)
    se_desactivo = estado_anterior and not activo
    
    try:
        # Si el código cambió, necesitamos crear nuevo registro y eliminar el viejo
        if nuevo_codigo != codigo_actual:
            print(f"🔄 Cambiando código: {codigo_actual} -> {nuevo_codigo}")
            
            # Crear nuevo vendedor con el nuevo código
            crear_vendedor(nuevo_codigo, {
                'nombre': nombre,
                'device_id': device_id,
                'activo': activo,
                'es_admin': es_admin,
                'fecha_creacion': vendedor_actual.get('fecha_creacion', datetime.now().isoformat()),
                'ultimo_acceso': vendedor_actual.get('ultimo_acceso'),
                'accesos_totales': vendedor_actual.get('accesos_totales', 0)
            })
            # Eliminar el viejo código - USAR LA NUEVA FUNCIÓN
            eliminar_vendedor_db(codigo_actual)
            codigo_final = nuevo_codigo
            
            # Invalidar sesiones del código viejo
            sesiones_invalidadas = invalidar_sesiones_vendedor(codigo_actual)
            
        else:
            # Solo actualizar datos si el código no cambió
            print(f"📝 Actualizando datos de: {codigo_actual}")
            actualizar_vendedor(codigo_actual, {
                'nombre': nombre,
                'device_id': device_id,
                'activo': activo,
                'es_admin': es_admin
            })
            codigo_final = codigo_actual
        
        # Registrar el cambio de código en accesos
        registrar_acceso('ADMIN', f'Cambio código: {codigo_actual} -> {nuevo_codigo}', True)
        
        # Si se DESACTIVÓ al vendedor, invalidar sus sesiones
        if se_desactivo:
            sesiones_cerradas = invalidar_sesiones_vendedor(codigo_final)
            registrar_acceso('ADMIN', f'Desactivación: {codigo_final} - {sesiones_cerradas} sesiones cerradas', True)
        
        # ✅ CRÍTICO: Sincronizar inmediatamente después de editar
        sincronizar_sqlite_a_json()
        
        # Si el usuario editó su propia cuenta, limpiar sesión
        if usuario_actual_editado:
            session.clear()
            return jsonify({
                'success': True,
                'mensaje': f'Tu código ha sido actualizado a: {nuevo_codigo}. Serás redirigido al login.',
                'nuevo_codigo': codigo_final,
                'sesion_cerrada': True,
                'redirect_url': url_for('login')
            })
        
        # Mensaje especial si se desactivó al vendedor
        if se_desactivo:
            mensaje = f'Vendedor {nombre} desactivado exitosamente. {sesiones_cerradas} sesión(es) cerrada(s).'
        else:
            mensaje = f'Vendedor {nombre} actualizado exitosamente'
        
        return jsonify({
            'success': True,
            'mensaje': mensaje,
            'nuevo_codigo': codigo_final,
            'sesion_cerrada': False,
            'vendedor_desactivado': se_desactivo
        })
        
    except Exception as e:
        print(f"❌ Error actualizando vendedor: {str(e)}")
        return jsonify({'error': f'Error actualizando vendedor: {str(e)}'}), 500

@app.route('/admin/desloguear-vendedor/<codigo>', methods=['POST'])
def desloguear_vendedor(codigo):
    """Forza el cierre de sesión de un vendedor"""
    if not vendedor_autenticado() or not es_administrador():
        return jsonify({'error': 'No autorizado'}), 403
    
    vendedor = obtener_vendedor(codigo)
    if not vendedor:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    # Invalidar TODAS las sesiones del vendedor
    sesiones_invalidadas = invalidar_sesiones_vendedor(codigo)
    
    registrar_acceso('ADMIN', f'Deslogueo forzado: {codigo} - {sesiones_invalidadas} sesiones cerradas', True)
    
    return jsonify({
        'success': True,
        'mensaje': f'Sesión cerrada forzadamente para {vendedor["nombre"]}. {sesiones_invalidadas} sesión(es) invalidada(s).',
        'sesiones_invalidadas': sesiones_invalidadas
    })

@app.route('/admin/eliminar-vendedor/<codigo>', methods=['POST'])
def eliminar_vendedor(codigo):
    """Elimina un vendedor"""
    if not vendedor_autenticado() or not es_administrador():
        return jsonify({'error': 'No autorizado'}), 403
    
    vendedor = obtener_vendedor(codigo)
    if not vendedor:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    nombre = vendedor['nombre']
    
    try:
        eliminar_vendedor_db(codigo)  # USAR LA NUEVA FUNCIÓN
        
        # Invalidar sesiones al eliminar
        invalidar_sesiones_vendedor(codigo)
        
        # ✅ CRÍTICO: Sincronizar inmediatamente después de eliminar
        sincronizar_sqlite_a_json()
        
        return jsonify({
            'success': True,
            'mensaje': f'Vendedor {nombre} eliminado exitosamente'
        })
    except Exception as e:
        return jsonify({'error': f'Error eliminando vendedor: {str(e)}'}), 500

@app.route('/admin/vendedores')
def listar_vendedores():
    """API para listar vendedores (JSON)"""
    if not vendedor_autenticado() or not es_administrador():
        return jsonify({'error': 'No autorizado'}), 403
    return jsonify(cargar_vendedores())

@app.route('/admin/historial-accesos')
def historial_accesos():
    """Obtiene el historial completo de accesos"""
    if not vendedor_autenticado() or not es_administrador():
        return jsonify({'error': 'No autorizado'}), 403
    
    conn = get_db_connection()
    accesos = conn.execute('SELECT * FROM accesos ORDER BY fecha_hora DESC LIMIT 1000').fetchall()
    conn.close()
    return jsonify([dict(a) for a in accesos])

# ================= RUTAS GENERALES =================

@app.route('/obtener-id')
def obtener_id():
    """Página para que los vendedores obtengan su deviceId"""
    return render_template('obtener-id.html')

@app.route('/logout')
def logout():
    """Cierra la sesión"""
    if 'vendedor_id' in session:
        invalidar_sesiones_vendedor(session['vendedor_id'])
    session.clear()
    return redirect(url_for('login'))

# ================= NUEVO: ENDPOINT DE SINCRONIZACIÓN MANUAL =================
@app.route('/admin/sincronizar-backup', methods=['POST'])
def sincronizar_backup():
    """Sincroniza manualmente la base de datos con el backup JSON"""
    if not vendedor_autenticado() or not es_administrador():
        return jsonify({'error': 'No autorizado'}), 403
    
    try:
        sincronizar_sqlite_a_json()
        return jsonify({
            'success': True,
            'mensaje': 'Backup sincronizado exitosamente'
        })
    except Exception as e:
        return jsonify({'error': f'Error sincronizando: {str(e)}'}), 500

# ================= CONFIGURACIÓN PARA PRODUCCIÓN =================
if __name__ == '__main__':
    # Para desarrollo local
    app.run(debug=False, host='0.0.0.0', port=5000)