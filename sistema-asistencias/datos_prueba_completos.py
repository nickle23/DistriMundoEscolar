import sqlite3
from datetime import datetime, timedelta

def generar_datos_completos():
    conn = sqlite3.connect('asistencias.db')
    cursor = conn.cursor()
    
    # Trabajador de prueba
    dni = '12345678'
    mes = 1  # Enero
    anio = 2024
    
    print("🗑️ Eliminando datos antiguos de enero 2024...")
    cursor.execute("DELETE FROM asistencias WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?", 
                   (dni, str(anio), str(mes).zfill(2)))
    
    print("📅 Generando asistencias para enero 2024...")
    
    # Generar para todos los días laborables de enero
    for dia in range(1, 32):
        fecha = datetime(2024, 1, dia)
        
        # Solo días laborables (lunes a viernes)
        if fecha.weekday() < 5:  # 0=lunes, 4=viernes
            
            # Crear diferentes escenarios INCLUYENDO FALTAS
            if dia in [2, 3]:  # Faltas los días 2 y 3 de enero
                entrada = None
                salida = None
                estado = 'FALTA'
                horas_extras = 0
                horas_trabajadas = 0
                observaciones = None
                
                # Insertar falta
                cursor.execute('''
                    INSERT INTO asistencias (dni, fecha, entrada, salida, horas_trabajadas, horas_extras, estado, tipo_registro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'MANUAL')
                ''', (dni, fecha.date(), entrada, salida, horas_trabajadas, horas_extras, estado))
                
                print(f"❌ {fecha.date()}: FALTA - Puedes justificarla en el panel admin")
                
            elif dia in [9, 10]:  # Faltas justificables los días 9 y 10
                entrada = None
                salida = None
                estado = 'FALTA'
                horas_extras = 0
                horas_trabajadas = 0
                observaciones = "Falta por enfermedad - pendiente de justificación"
                
                # Insertar falta con observaciones
                cursor.execute('''
                    INSERT INTO asistencias (dni, fecha, entrada, salida, horas_trabajadas, horas_extras, estado, observaciones, tipo_registro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'MANUAL')
                ''', (dni, fecha.date(), entrada, salida, horas_trabajadas, horas_extras, estado, observaciones))
                
                print(f"⚠️ {fecha.date()}: FALTA JUSTIFICABLE - {observaciones}")
                
            elif dia % 10 == 1:  # Días normales
                entrada = '08:00:00'
                salida = '19:00:00'
                estado = 'NORMAL'
                horas_extras = 0
                observaciones = None
                
            elif dia % 10 == 2:  # Tardanzas
                entrada = '08:25:00'
                salida = '19:00:00'
                estado = 'TARDE'
                horas_extras = 0
                observaciones = "Llegada tarde por tráfico"
                
            elif dia % 10 == 3:  # Horas extras
                entrada = '08:00:00'
                salida = '21:00:00'  # 2 horas extra
                estado = 'NORMAL'
                horas_extras = 2
                observaciones = "Horas extras por inventario"
                
            elif dia % 10 == 4:  # Muchas horas extras
                entrada = '08:00:00'
                salida = '23:00:00'  # 4 horas extra
                estado = 'NORMAL'
                horas_extras = 4
                observaciones = "Proyecto especial - horario extendido"
                
            elif dia % 10 == 5:  # Tardanza + horas extras
                entrada = '08:20:00'
                salida = '20:30:00'  # 1.5 horas extra
                estado = 'TARDE'
                horas_extras = 1.5
                observaciones = "Tardanza con horas extras compensatorias"
                
            else:  # Días normales
                entrada = '08:00:00'
                salida = '19:00:00'
                estado = 'NORMAL'
                horas_extras = 0
                observaciones = None
            
            # Solo calcular horas si no es falta
            if estado != 'FALTA':
                horas_trabajadas = 11 + horas_extras
                
                # Insertar asistencia normal
                cursor.execute('''
                    INSERT INTO asistencias (dni, fecha, entrada, salida, horas_trabajadas, horas_extras, estado, observaciones, tipo_registro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'MANUAL')
                ''', (dni, fecha.date(), entrada, salida, horas_trabajadas, horas_extras, estado, observaciones))
                
                print(f"✅ {fecha.date()}: {entrada} - {salida} | Estado: {estado} | Extras: {horas_extras}h")
    
    conn.commit()
    
    # Contar estadísticas
    cursor.execute("SELECT COUNT(*) FROM asistencias WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?", 
                   (dni, str(anio), str(mes).zfill(2)))
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM asistencias WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ? AND estado = 'FALTA'", 
                   (dni, str(anio), str(mes).zfill(2)))
    faltas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM asistencias WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ? AND estado = 'TARDE'", 
                   (dni, str(anio), str(mes).zfill(2)))
    tardanzas = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(horas_extras) FROM asistencias WHERE dni = ? AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?", 
                   (dni, str(anio), str(mes).zfill(2)))
    total_horas_extras = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"\n🎉 DATOS DE PRUEBA GENERADOS EXITOSAMENTE")
    print(f"👤 Trabajador: 12345678 - Juan Pérez García")
    print(f"📅 Mes: Enero 2024")
    print(f"📊 Total días registrados: {total}")
    print(f"❌ Faltas: {faltas} días")
    print(f"⚠️ Tardanzas: {tardanzas} días")
    print(f"⏱️ Horas extras totales: {total_horas_extras}h")
    print(f"💰 Sueldo base: S/ 1800.00")
    
    print(f"\n🔍 PARA PROBAR EN EL PANEL ADMIN:")
    print(f"   1. Ve a 'Gestión Histórica'")
    print(f"   2. Filtra por DNI: 12345678")
    print(f"   3. Filtra por Mes: 1 (Enero)")
    print(f"   4. Filtra por Estado: 'FALTA' para ver las faltas")
    print(f"   5. Usa el botón '📝 Justificar' en las faltas")
    print(f"   6. Genera reportes para ver estadísticas completas")

if __name__ == '__main__':
    generar_datos_completos()