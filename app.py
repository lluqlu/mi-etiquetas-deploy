from flask import Flask, render_template, request, send_file, redirect, url_for
import qrcode
import sqlite3
import os
import csv
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import portrait

app = Flask(__name__)

# --------- DB INIT --------- #
def init_db():
    conn = sqlite3.connect('seguimiento.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS contador (id INTEGER PRIMARY KEY, secuencia INTEGER)''')
    c.execute('''INSERT OR IGNORE INTO contador (id, secuencia) VALUES (1, 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS envios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_seguimiento TEXT,
                    remitente TEXT,
                    dni_rem TEXT,
                    celular_rem TEXT,
                    destinatario TEXT,
                    dni_dest TEXT,
                    cp_dest TEXT,
                    peso TEXT,
                    fragil INTEGER,
                    observaciones TEXT
                )''')
    conn.commit()
    conn.close()


init_db()

# --------- CONTADOR --------- #
def get_next_tracking(cp_dest):
    conn = sqlite3.connect('seguimiento.db')
    c = conn.cursor()
    c.execute('SELECT secuencia FROM contador WHERE id=1')
    secuencia = c.fetchone()[0] + 1
    c.execute('UPDATE contador SET secuencia = ? WHERE id=1', (secuencia,))
    conn.commit()
    conn.close()
    return f"AR-{cp_dest}-{str(secuencia).zfill(2)}"

# --------- FLASK --------- #
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        modo = request.form.get('modo')
        datos = {
            'remitente': request.form.get('remitente'),
            'dni_rem': request.form.get('dni_rem'),
            'celular_rem': request.form.get('celular_rem'),
            'direccion_rem': request.form.get('direccion_rem'),
            'cp_rem': request.form.get('cp_rem'),
            'ciudad_rem': request.form.get('ciudad_rem'),
            'prov_rem': request.form.get('prov_rem'),
            'destinatario': request.form.get('destinatario'),
            'dni_dest': request.form.get('dni_dest'),
            'direccion_dest': request.form.get('direccion_dest'),
            'cp_dest': request.form.get('cp_dest'),
            'ciudad_dest': request.form.get('ciudad_dest'),
            'prov_dest': request.form.get('prov_dest'),
            'celular_dest': request.form.get('celular_dest'),
            'peso': request.form.get('peso'),
            'fragil': request.form.get('fragil') == 'si',
            'observaciones': request.form.get('observaciones')[:50] if request.form.get('observaciones') else ""
        }
        generar_etiqueta_envio(datos, modo)
        return send_file("etiqueta_envio.pdf", as_attachment=True)

    return render_template('formulario.html')

# --------- PDF --------- #
def generar_qr_llamada(celular_dest, archivo_salida="static/qr.png"):
    qr = qrcode.make(f"tel:{celular_dest}")
    qr.save(archivo_salida)

def generar_etiqueta_envio(data, modo, archivo_salida="etiqueta_envio.pdf"):
    generar_qr_llamada(data['celular_dest'])

    if modo == '1':
        numero_seguimiento = get_next_tracking(data['cp_dest'])
    else:
        numero_seguimiento = "-"

    registrar_envio(data, numero_seguimiento)

    c = canvas.Canvas(archivo_salida, pagesize=portrait((283, 425)))

    if modo == '1':
        c.setFont("Helvetica-Bold", 8)
        c.drawString(180, 415, f"TRACK: {numero_seguimiento}")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(200, 405, f"PESO: {data['peso']}KG")

    c.drawImage("static/qr.png", 20, 340, width=80, height=80)

    if data['fragil']:
        c.drawImage("static/flecha_arriba.png", 200, 340, width=50, height=40)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(20, 320, "REMITENTE")
    c.setFont("Helvetica", 8)
    c.drawString(20, 308, data['remitente'])
    c.drawString(20, 295, f"DNI: {data['dni_rem']}")
    c.drawString(20, 282, f"Cel: {data['celular_rem']}")
    c.drawString(20, 270, data['direccion_rem'])
    c.drawString(20, 257, f"CP: {data['cp_rem']} - {data['ciudad_rem']} - {data['prov_rem']}")

    c.line(15, 250, 270, 250)

    if modo == '1':
        barcode = code128.Code128(numero_seguimiento, barHeight=50, barWidth=1.2)
        barcode.drawOn(c, 100, 215)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(150, 200, numero_seguimiento)
    c.line(15, 190, 270, 190)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(20, 175, "DESTINATARIO")
    c.setFont("Helvetica", 8)
    c.drawString(20, 162, data['destinatario'])
    c.drawString(20, 149, f"DNI: {data['dni_dest']}")
    c.drawString(20, 136, f"Cel: {data['celular_dest']}")
    c.drawString(20, 123, data['direccion_dest'])

    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(260, 123, f"CP: {data['cp_dest']}")

    c.setFont("Helvetica", 8)
    c.drawString(20, 110, f"{data['ciudad_dest'].upper()} - {data['prov_dest'].upper()}")

    c.line(15, 100, 270, 100)

    if data['fragil']:
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(140, 80, "⚠ FRÁGIL - MANIPULAR CON CUIDADO ⚠")
        c.drawImage("static/fragil.png", 115, 40, width=50, height=40)

    if data['observaciones']:
        c.setFont("Helvetica", 8)
        c.drawString(20, 25, f"OBS: {data['observaciones']}")

    c.save()

# --------- DASHBOARD --------- #
@app.route('/historial')
def historial():
    conn = sqlite3.connect('seguimiento.db')
    c = conn.cursor()
    c.execute("SELECT * FROM envios ORDER BY id DESC")
    envios = c.fetchall()
    conn.close()
    return render_template('historial.html', envios=envios)

@app.route('/export-csv')
def export_csv():
    conn = sqlite3.connect('seguimiento.db')
    c = conn.cursor()
    c.execute("SELECT * FROM envios ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    with open("envios.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Seguimiento", "Remitente", "DNI Rem", "Cel Rem", "Destinatario", "DNI Dest", "CP Dest", "Peso", "Frágil", "Observaciones"])
        writer.writerows(rows)
    return send_file("envios.csv", as_attachment=True)

# --------- REGISTRO --------- #
def registrar_envio(data, numero_seguimiento):
    conn = sqlite3.connect('seguimiento.db')
    c = conn.cursor()
    c.execute('''INSERT INTO envios (numero_seguimiento, remitente, dni_rem, celular_rem, destinatario, dni_dest, cp_dest, peso, fragil, observaciones)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (numero_seguimiento, data['remitente'], data['dni_rem'], data['celular_rem'], data['destinatario'], data['dni_dest'], data['cp_dest'], data['peso'], int(data['fragil']), data['observaciones']))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)
