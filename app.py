from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from database import get_db_connection

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura_admin_12345'

# ================= RUTAS PRINCIPALES =================
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
                return render_template('login.html', 
                                    error="❌ Dispositivo no autorizado")
        
        # Login exitoso
        session['vendedor_id'] = codigo
        session['vendedor_nombre'] = vendedor['nombre']
        session['es_admin'] = vendedor.get('es_admin', False)
        
        # Actualizar último acceso
        from datetime import datetime
        vendedor['ultimo_acceso'] = datetime.now().isoformat()
        vendedor['accesos_totales'] = vendedor.get('accesos_totales', 0) + 1
        
        # Guardar cambios en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE vendedores SET ultimo_acceso = %s, accesos_totales = %s 
            WHERE codigo = %s
        ''', (vendedor['ultimo_acceso'], vendedor['accesos_totales'], codigo))
        conn.commit()
        conn.close()
        
        if vendedor.get('es_admin', False):
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('distrimundoescolar'))
    else:
        return render_template('login.html', 
                            error="❌ Código inválido o cuenta desactivada")

# ... (el resto de tus rutas actuales)

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


# ... (el resto de rutas igual pero usando consultas parametrizadas)
