import sqlite3

conn = sqlite3.connect("seguimiento.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS seguimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seguimiento TEXT NOT NULL,
    fechahora TEXT NOT NULL,
    evento TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("Tabla 'seguimiento' creada o verificada correctamente.")

