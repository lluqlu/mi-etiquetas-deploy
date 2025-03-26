import sqlite3

# Crear conexión a una base local llamada datos.db
conn = sqlite3.connect("datos.db")
c = conn.cursor()

# Crear tabla para los envíos
c.execute('''
CREATE TABLE IF NOT EXISTS envios (
    seguimiento TEXT PRIMARY KEY,
    remitente TEXT,
    dni_rem TEXT,
    cel_rem TEXT,
    destinatario TEXT,
    dni_dest TEXT,
    cp_dest TEXT,
    peso TEXT,
    fragil INTEGER,
    observaciones TEXT
)
''')

# Crear tabla para los eventos de seguimiento
c.execute('''
CREATE TABLE IF NOT EXISTS seguimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seguimiento TEXT,
    fechahora TEXT,
    evento TEXT
)
''')

conn.commit()
conn.close()

print("Base de datos creada con las tablas necesarias ✅")

