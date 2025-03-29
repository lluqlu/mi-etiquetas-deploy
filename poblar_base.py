import sqlite3
import random
from datetime import datetime, timedelta

# Conexion
conn = sqlite3.connect("datos.db")
cursor = conn.cursor()

conn2 = sqlite3.connect("seguimiento.db")
cursor2 = conn2.cursor()

# Limpia ambas tablas
cursor.execute("DELETE FROM envios")
conn.commit()

cursor2.execute("DELETE FROM seguimiento")
conn2.commit()

# Datos base ficticios
nombres = ["Lucía", "Martín", "Sofía", "Matías", "Valentina", "Lautaro", "Camila", "Agustín", "Julieta", "Tomás"]
apellidos = ["Gómez", "Pérez", "Fernández", "López", "Martínez", "González", "Rodríguez", "Sánchez", "Romero", "Díaz"]
ciudades = [("Buenos Aires", "CABA", "1000"), ("Córdoba", "Córdoba", "5000"), ("Rosario", "Santa Fe", "2000"),
            ("Mendoza", "Mendoza", "5500"), ("La Plata", "Buenos Aires", "1900"), ("San Miguel", "Buenos Aires", "1663")]
eventos_posibles = ["En preparación", "Listo para despachar", "En tránsito", "Llegó a sucursal", "Entregado"]

def generar_envio(n):
    rem_nombre = f"{random.choice(nombres)} {random.choice(apellidos)}"
    dest_nombre = f"{random.choice(nombres)} {random.choice(apellidos)}"

    ciudad_rem, prov_rem, cp_rem = random.choice(ciudades)
    ciudad_dest, prov_dest, cp_dest = random.choice(ciudades)

    seguimiento = f"AR-{cp_dest}-{str(n).zfill(2)}"

    data = (
        seguimiento,
        rem_nombre,
        random.randint(20000000, 45000000),  # DNI Rem
        f"11{random.randint(40000000,49999999)}",  # Cel rem
        dest_nombre,
        random.randint(20000000, 45000000),  # DNI Dest
        cp_dest,
        round(random.uniform(0.5, 3.0), 2),  # peso
        random.choice([0, 1]),  # frágil
        random.choice(["", "", "No dejar bajo el sol", "Entregar al portero"]),
        f"Calle {random.randint(1, 500)}",  # dir rem
        cp_rem,
        ciudad_rem,
        prov_rem,
        f"Calle {random.randint(1, 500)}",  # dir dest
        ciudad_dest,
        prov_dest,
        f"11{random.randint(40000000,49999999)}",  # Cel dest
        random.choice(["", "", f"{random.randint(3600000000000000, 3600009999999999)}"])
    )

    return data

def generar_eventos(seguimiento):
    cantidad = random.randint(2, 4)
    fecha_base = datetime.now() - timedelta(days=random.randint(1, 10))
    eventos = []
    for i in range(cantidad):
        evento = random.choice(eventos_posibles)
        fecha = fecha_base + timedelta(hours=5*i)
        eventos.append((seguimiento, fecha.strftime("%Y-%m-%d %H:%M:%S"), evento))
    return eventos

# Carga masiva
for i in range(1, 31):
    envio = generar_envio(i)
    cursor.execute("""
        INSERT INTO envios (
            seguimiento, remitente, dni_rem, cel_rem,
            destinatario, dni_dest, cp_dest, peso, fragil, observaciones,
            direccion_rem, cp_rem, ciudad_rem, prov_rem,
            direccion_dest, ciudad_dest, prov_dest, celular_dest, codigo_externo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, envio)

    eventos = generar_eventos(envio[0])
    for e in eventos:
        cursor2.execute("INSERT INTO seguimiento (seguimiento, fechahora, evento) VALUES (?, ?, ?)", e)

# Confirmar
conn.commit()
conn2.commit()
conn.close()
conn2.close()
print("✔️ Base de datos poblada con 30 envíos ficticios.")

