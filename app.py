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

# ================= RUTAS PÚBLICAS =================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'vendedor_id' in session:
        return redirect(url_for('distrimundoescolar'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def autenticar():
    codigo = request.form.get('codigo', '').strip().upper()
    dispositivo = request.form.get('dispositivo', '').strip()
    
    vendedor = obtener_vendedor(codigo)
    
    if vendedor and vendedor.get('activo', True):
        # Verificar device_id si está configurado
        if vendedor.get('device_id') and vendedor['device_id'].strip():
            if vendedor['device_id'] != dispositivo:
                registrar_acceso(codigo, dispositivo, False)
                return render_template('login.html', 
                                    error="❌ Dispositivo no autorizado")
        
        # Login exitoso
        session['vendedor_id'] = codigo
        session['vendedor_nombre'] = vendedor['nombre']
        session['es_admin'] = vendedor.get('es_admin', False)
        
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
    if 'vendedor_id' not in session:
        return redirect(url_for('login'))
    return render_template('distrimundoescolar.html')

@app.route('/promociones')
def promociones():
    """Página de promociones"""
    if 'vendedor_id' not in session:
        return redirect(url_for('login'))
    return render_template('promociones.html')

@app.route('/nosotros')
def nosotros():
    """Página nosotros"""
    if 'vendedor_id' not in session:
        return redirect(url_for('login'))
    return render_template('nosotros.html')

@app.route('/contacto')
def contacto():
    """Página contacto"""
    if 'vendedor_id' not in session:
        return redirect(url_for('login'))
    return render_template('contacto.html')

# ================= PANEL ADMINISTRADOR =================
@app.route('/admin')
def admin_panel():
    """Panel de administración"""
    if 'vendedor_id' not in session or not session.get('es_admin'):
        return redirect(url_for('login'))
    return render_template('admin_panel.html')

@app.route('/admin/agregar-vendedor', methods=['POST'])
def agregar_vendedor():
    """Agrega un nuevo vendedor"""
    if 'vendedor_id' not in session or not session.get('es_admin'):
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

@app.route('/admin/editar-vendedor/<codigo_actual>', methods=['POST'])
def editar_vendedor(codigo_actual):
    """Edita un vendedor existente"""
    if 'vendedor_id' not in session or not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    vendedor_actual = obtener_vendedor(codigo_actual)
    if not vendedor_actual:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    nuevo_codigo = request.form.get('nuevo_codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    device_id = request.form.get('device_id', '').strip()
    activo = request.form.get('activo') == 'on'
    es_admin = request.form.get('es_admin') == 'on'
    
    # Validar que el nuevo código no esté en uso
    if nuevo_codigo != codigo_actual and obtener_vendedor(nuevo_codigo):
        return jsonify({'error': 'El nuevo código ya está en uso'}), 400
    
    try:
        if nuevo_codigo != codigo_actual:
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
        else:
            # Solo actualizar datos
            actualizar_vendedor(codigo_actual, {
                'nombre': nombre,
                'device_id': device_id,
                'activo': activo,
                'es_admin': es_admin
            })
        
        return jsonify({
            'success': True,
            'mensaje': f'Vendedor {nombre} actualizado exitosamente'
        })
    except Exception as e:
        return jsonify({'error': f'Error actualizando vendedor: {str(e)}'}), 500

@app.route('/admin/eliminar-vendedor/<codigo>', methods=['POST'])
def eliminar_vendedor(codigo):
    """Elimina un vendedor"""
    if 'vendedor_id' not in session or not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    vendedor = obtener_vendedor(codigo)
    if not vendedor:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    try:
        eliminar_vendedor_db(codigo)
        return jsonify({
            'success': True,
            'mensaje': f'Vendedor {vendedor["nombre"]} eliminado exitosamente'
        })
    except Exception as e:
        return jsonify({'error': f'Error eliminando vendedor: {str(e)}'}), 500

@app.route('/admin/vendedores')
def listar_vendedores():
    """API para listar vendedores (JSON)"""
    if 'vendedor_id' not in session or not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    return jsonify(cargar_vendedores())

@app.route('/admin/historial-accesos')
def historial_accesos():
    """Obtiene el historial completo de accesos"""
    if 'vendedor_id' not in session or not session.get('es_admin'):
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