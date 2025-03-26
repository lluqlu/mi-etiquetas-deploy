import sqlite3

# Conectar a la base de datos existente
db = sqlite3.connect("datos.db")
cursor = db.cursor()

# Agregar nuevas columnas si no existen
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN direccion_rem TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN cp_rem TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN ciudad_rem TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN prov_rem TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN direccion_dest TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN ciudad_dest TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN prov_dest TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE envios ADD COLUMN celular_dest TEXT")
except sqlite3.OperationalError:
    pass

# Guardar cambios y cerrar conexión
db.commit()
db.close()

print("Migración completada con éxito.")

