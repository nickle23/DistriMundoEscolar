from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from database import get_db_connection

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura_admin_12345'

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