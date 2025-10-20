from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import os
from datetime import datetime
from database import get_db_connection

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura_admin_12345'

# ================= FUNCIONES AUXILIARES =================
def obtener_vendedor(codigo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendedores WHERE codigo = %s", (codigo,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'codigo': result[0],
            'nombre': result[1],
            'device_id': result[2],
            'activo': result[3],
            'es_admin': result[4],
            'fecha_creacion': result[5],
            'ultimo_acceso': result[6],
            'accesos_totales': result[7]
        }
    return None

# ✅ FUNCIÓN MEJORADA: Verifica credenciales en tiempo real
def credenciales_coinciden(vendedor_id, dispositivo_actual):
    """Verifica si las credenciales actuales coinciden con la BD"""
    vendedor = obtener_vendedor(vendedor_id)
    if not vendedor:
        print(f"❌ Vendedor {vendedor_id} no encontrado en BD")
        return False
    
    # Verificar si el vendedor está activo
    if not vendedor.get('activo', True):
        print(f"❌ Vendedor {vendedor_id} está INACTIVO")
        return False
    
    # Verificar Device ID si está configurado
    if vendedor.get('device_id') and vendedor['device_id'].strip():
        coincide = vendedor['device_id'] == dispositivo_actual
        if not coincide:
            print(f"❌ Device ID no coincide: BD='{vendedor['device_id']}', Sesión='{dispositivo_actual}'")
        return coincide
    
    print(f"✅ Credenciales válidas para {vendedor_id}")
    return True

def cargar_vendedores():
    """Carga todos los vendedores desde la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendedores")
    results = cursor.fetchall()
    conn.close()
    
    vendedores = {}
    for result in results:
        vendedores[result[0]] = {
            'codigo': result[0],
            'nombre': result[1],
            'device_id': result[2],
            'activo': result[3],
            'es_admin': result[4],
            'fecha_creacion': result[5],
            'ultimo_acceso': result[6],
            'accesos_totales': result[7]
        }
    return vendedores

def actualizar_vendedor(codigo, datos):
    """Actualiza los datos de un vendedor"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE vendedores 
        SET nombre = %s, device_id = %s, activo = %s, es_admin = %s, ultimo_acceso = %s, accesos_totales = %s
        WHERE codigo = %s
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
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vendedores 
        (codigo, nombre, device_id, activo, es_admin, fecha_creacion, accesos_totales)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
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
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vendedores WHERE codigo = %s', (codigo,))
    conn.commit()
    conn.close()

def registrar_acceso(vendedor_id, dispositivo, exitoso, ip=None):
    """Registra un intento de acceso en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO accesos (vendedor_id, dispositivo, exitoso, ip)
        VALUES (%s, %s, %s, %s)
    ''', (vendedor_id, dispositivo, exitoso, ip or request.remote_addr))
    conn.commit()
    conn.close()

def registrar_sesion(vendedor_id, dispositivo, ip=None):
    """Registra una nueva sesión activa"""
    sesion_id = f"{vendedor_id}_{dispositivo}_{datetime.now().timestamp()}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sesiones_activas (sesion_id, vendedor_id, dispositivo, ip)
        VALUES (%s, %s, %s, %s)
    ''', (sesion_id, vendedor_id, dispositivo, ip or request.remote_addr))
    conn.commit()
    conn.close()
    return sesion_id

def invalidar_sesiones_vendedor(vendedor_id):
    """Invalida TODAS las sesiones de un vendedor"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sesiones_activas SET activa = FALSE, fecha_fin = %s WHERE vendedor_id = %s AND activa = TRUE',
        (datetime.now().isoformat(), vendedor_id)
    )
    sesiones_invalidadas = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"🚫 Invalidadas {sesiones_invalidadas} sesiones para {vendedor_id}")
    return sesiones_invalidadas

def sesion_es_valida(vendedor_id, dispositivo_actual, vendedor_device_id):
    """Verifica si la sesión actual es válida"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Usar dispositivo_actual si el vendedor no tiene Device ID configurado
    dispositivo_buscar = vendedor_device_id if vendedor_device_id else dispositivo_actual
    
    cursor.execute(
        'SELECT * FROM sesiones_activas WHERE vendedor_id = %s AND dispositivo = %s AND activa = TRUE',
        (vendedor_id, dispositivo_buscar)
    )
    sesion = cursor.fetchone()
    conn.close()
    
    valida = sesion is not None
    print(f"🔍 Sesión válida para {vendedor_id}: {valida}")
    return valida

# ✅ FUNCIÓN COMPLETAMENTE REESCRITA - DETECCIÓN EN TIEMPO REAL
def vendedor_autenticado():
    """Verifica si el usuario está autenticado Y tiene sesión válida"""
    if 'vendedor_id' not in session:
        print("❌ No hay vendedor_id en sesión")
        return False
    
    vendedor_id = session.get('vendedor_id')
    dispositivo_actual = session.get('dispositivo_actual', '')
    
    print(f"🔐 Verificando autenticación para: {vendedor_id}, dispositivo: {dispositivo_actual}")
    
    # VERIFICACIÓN CRÍTICA MEJORADA: ¿Las credenciales aún coinciden?
    if not credenciales_coinciden(vendedor_id, dispositivo_actual):
        # Credenciales cambiadas - cerrar sesión inmediatamente
        print(f"🚨 SESIÓN INVALIDADA: Credenciales cambiadas para {vendedor_id}")
        # Invalidar sesiones en BD también
        invalidar_sesiones_vendedor(vendedor_id)
        session.clear()
        return False
    
    vendedor = obtener_vendedor(vendedor_id)
    if not vendedor:
        print(f"❌ Vendedor {vendedor_id} no existe en BD")
        session.clear()
        return False
    
    # Si es administrador, bypass de seguridad de sesiones activas (pero NO de credenciales)
    if vendedor.get('es_admin', False):
        print(f"✅ Admin {vendedor_id} autenticado (bypass sesiones activas)")
        return True
    
    # Verificar si la sesión sigue siendo válida para usuarios normales
    vendedor_device_id = vendedor.get('device_id', '')
    sesion_valida = sesion_es_valida(vendedor_id, dispositivo_actual, vendedor_device_id)
    
    if not sesion_valida:
        print(f"❌ Sesión NO válida para {vendedor_id}")
        session.clear()
    
    return sesion_valida

# ================= RUTAS PÚBLICAS =================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if vendedor_autenticado():
        return redirect(url_for('distrimundoescolar'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def autenticar():
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
        registrar_sesion(codigo, dispositivo)
        
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

@app.route('/obtener-id')
def obtener_id():
    """Página para que los vendedores obtengan su deviceId"""
    return render_template('obtener-id.html')

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
    if not vendedor_autenticado() or not session.get('es_admin'):
        return redirect(url_for('login'))
    return render_template('admin_panel.html')

@app.route('/admin/agregar-vendedor', methods=['POST'])
def agregar_vendedor():
    """Agrega un nuevo vendedor"""
    if not vendedor_autenticado() or not session.get('es_admin'):
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
        
        return jsonify({
            'success': True,
            'mensaje': f'Vendedor {nombre} agregado exitosamente',
            'codigo': codigo
        })
    except Exception as e:
        return jsonify({'error': f'Error guardando el vendedor: {str(e)}'}), 500

# ✅ RUTA COMPLETAMENTE REESCRITA - INVALIDACIÓN INMEDIATA GARANTIZADA
@app.route('/admin/editar-vendedor/<codigo_actual>', methods=['POST'])
def editar_vendedor(codigo_actual):
    """Edita un vendedor existente - CORREGIDA"""
    if not vendedor_autenticado() or not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    vendedor_actual = obtener_vendedor(codigo_actual)
    if not vendedor_actual:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    nuevo_codigo = request.form.get('nuevo_codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    device_id = request.form.get('device_id', '').strip()
    activo = request.form.get('activo') == 'on'
    es_admin = request.form.get('es_admin') == 'on'
    
    # ✅ DETECCIÓN MEJORADA: Si el usuario editado es el MISMO que está logeado
    es_usuario_actual = (codigo_actual == session.get('vendedor_id'))
    print(f"🔍 Editando usuario actual: {es_usuario_actual} (sesión: {session.get('vendedor_id')})")
    
    # Validar que el nuevo código no esté en uso
    if nuevo_codigo != codigo_actual and obtener_vendedor(nuevo_codigo):
        return jsonify({'error': 'El nuevo código ya está en uso'}), 400
    
    estado_anterior = vendedor_actual.get('activo', True)
    se_desactivo = estado_anterior and not activo
    
    # ✅ DETECCIÓN MEJORADA: Credenciales cambiadas
    credenciales_cambiadas = (
        nuevo_codigo != codigo_actual or 
        device_id != vendedor_actual.get('device_id', '')
    )
    
    print(f"🔍 Credenciales cambiadas: {credenciales_cambiadas} (código: {nuevo_codigo != codigo_actual}, device_id: {device_id != vendedor_actual.get('device_id', '')})")
    
    try:
        if nuevo_codigo != codigo_actual:
            print(f"🔄 Cambiando código de {codigo_actual} a {nuevo_codigo}")
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
            # Eliminar el viejo código
            eliminar_vendedor_db(codigo_actual)
            codigo_final = nuevo_codigo
            
            # ✅ INVALIDACIÓN INMEDIATA del código viejo
            sesiones_invalidadas = invalidar_sesiones_vendedor(codigo_actual)
            print(f"🚫 Sesiones invalidadas del código viejo: {sesiones_invalidadas}")
            
        else:
            print(f"✏️ Actualizando datos de {codigo_actual}")
            # Solo actualizar datos
            actualizar_vendedor(codigo_actual, {
                'nombre': nombre,
                'device_id': device_id,
                'activo': activo,
                'es_admin': es_admin
            })
            codigo_final = codigo_actual
        
        # Si se DESACTIVÓ al vendedor, invalidar sus sesiones
        if se_desactivo:
            sesiones_cerradas = invalidar_sesiones_vendedor(codigo_final)
            print(f"🚫 Vendedor desactivado - sesiones cerradas: {sesiones_cerradas}")
        
        # ✅ RESPUESTA MEJORADA: Forzar recarga si es el usuario actual
        respuesta = {
            'success': True,
            'mensaje': f'Vendedor {nombre} actualizado exitosamente'
        }
        
        if es_usuario_actual:
            if credenciales_cambiadas:
                print("🔄 Usuario actual cambió sus credenciales - forzando recarga")
                respuesta['recargar_pagina'] = True
                respuesta['mensaje'] += ' Se recargará la página porque modificaste tus credenciales.'
                # Invalidar sesiones actuales inmediatamente
                invalidar_sesiones_vendedor(codigo_final)
            else:
                print("ℹ️ Usuario actual editó sus datos (sin cambiar credenciales)")
        
        return jsonify(respuesta)
        
    except Exception as e:
        print(f"❌ Error actualizando vendedor: {str(e)}")
        return jsonify({'error': f'Error actualizando vendedor: {str(e)}'}), 500

@app.route('/admin/desloguear-vendedor/<codigo>', methods=['POST'])
def desloguear_vendedor(codigo):
    """Forza el cierre de sesión de un vendedor"""
    if not vendedor_autenticado() or not session.get('es_admin'):
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

# ✅ RUTA MEJORADA: Protección del admin principal
@app.route('/admin/eliminar-vendedor/<codigo>', methods=['POST'])
def eliminar_vendedor(codigo):
    """Elimina un vendedor - CON PROTECCIÓN DEL ADMIN PRINCIPAL"""
    if not vendedor_autenticado() or not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    # ✅ PROTECCIÓN CRÍTICA: No permitir eliminar al admin principal
    if codigo == 'DARKEYES':
        return jsonify({'error': 'No se puede eliminar al administrador principal'}), 400
    
    vendedor = obtener_vendedor(codigo)
    if not vendedor:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    try:
        eliminar_vendedor_db(codigo)
        
        # Invalidar sesiones al eliminar
        invalidar_sesiones_vendedor(codigo)
        
        return jsonify({
            'success': True,
            'mensaje': f'Vendedor {vendedor["nombre"]} eliminado exitosamente'
        })
    except Exception as e:
        return jsonify({'error': f'Error eliminando vendedor: {str(e)}'}), 500

@app.route('/admin/vendedores')
def listar_vendedores():
    """API para listar vendedores (JSON)"""
    if not vendedor_autenticado() or not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    return jsonify(cargar_vendedores())

@app.route('/admin/historial-accesos')
def historial_accesos():
    """Obtiene el historial completo de accesos"""
    if not vendedor_autenticado() or not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT vendedor_id, dispositivo, exitoso, fecha_hora, ip 
        FROM accesos 
        ORDER BY fecha_hora DESC 
        LIMIT 100
    ''')
    results = cursor.fetchall()
    conn.close()
    
    accesos = []
    for result in results:
        accesos.append({
            'vendedor_id': result[0],
            'dispositivo': result[1],
            'exitoso': result[2],
            'fecha_hora': result[3],
            'ip': result[4]
        })
    
    return jsonify(accesos)

# ================= RUTAS GENERALES =================
@app.route('/logout')
def logout():
    """Cierra la sesión"""
    if 'vendedor_id' in session:
        invalidar_sesiones_vendedor(session['vendedor_id'])
    session.clear()
    return redirect(url_for('login'))

# ================= RUTAS PARA SERVIR ARCHIVOS =================
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory('data', filename)

@app.route('/img/<path:filename>')
def serve_img(filename):
    return send_from_directory('img', filename)

# ================= CONFIGURACIÓN =================
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)