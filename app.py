from flask import Flask, render_template, request, send_file, redirect, url_for, Response, session
import qrcode
import json
import os
import csv
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import portrait
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "etiqueta_secreta")

# --------- AUTENTICACIÓN BÁSICA --------- #
def check_auth(username, password):
    return username == os.getenv("USUARIO") and password == os.getenv("CLAVE")

def authenticate():
    return Response(
        'Acceso restringido.\nNecesitás iniciar sesión.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

# --------- CONTADOR JSON PERSISTENTE --------- #
def get_next_tracking(cp_dest):
    ruta = "static/contador.json"
    if not os.path.exists(ruta):
        with open(ruta, "w") as f:
            json.dump({"secuencia": 0}, f)

    with open(ruta, "r") as f:
        datos = json.load(f)

    datos["secuencia"] += 1

    with open(ruta, "w") as f:
        json.dump(datos, f)

    return f"AR-{cp_dest}-{str(datos['secuencia']).zfill(2)}"

# --------- REGISTRO --------- #
def registrar_envio(data, numero_seguimiento):
    with open("static/envios.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if os.stat("static/envios.csv").st_size == 0:
            writer.writerow(["Seguimiento", "Remitente", "DNI Rem", "Cel Rem", "Destinatario", "DNI Dest", "CP Dest", "Peso", "Frágil", "Observaciones"])
        writer.writerow([
            numero_seguimiento,
            data['remitente'],
            data['dni_rem'],
            data['celular_rem'],
            data['destinatario'],
            data['dni_dest'],
            data['cp_dest'],
            data['peso'],
            int(data['fragil']),
            data['observaciones']
        ])

# --------- HISTORIAL --------- #
@app.route('/historial')
@requires_auth
def historial():
    envios = []
    try:
        with open("static/envios.csv", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                envios.append(row)
    except FileNotFoundError:
        pass
    return render_template("historial.html", envios=envios)

@app.route('/export-csv')
@requires_auth
def export_csv():
    return send_file("static/envios.csv", as_attachment=True)

# --------- PDF --------- #
def generar_qr_llamada(celular_dest, archivo_salida="static/qr.png"):
    qr = qrcode.make(f"tel:{celular_dest}")
    qr.save(archivo_salida)

# --------- ETIQUETA --------- #
def generar_etiqueta_envio(data, modo, archivo_salida="etiqueta_envio.pdf"):
    generar_qr_llamada(data['celular_dest'])

    if modo == '1' or modo == '3':
        numero_seguimiento = get_next_tracking(data['cp_dest'])
    else:
        numero_seguimiento = "-"

    registrar_envio(data, numero_seguimiento)

    c = canvas.Canvas(archivo_salida, pagesize=portrait((283, 425)))

    if modo == '1' or modo == '3':
        c.setFont("Helvetica-Bold", 8)
        c.drawString(180, 415, f"TRACK: {numero_seguimiento}")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(200, 405, f"PESO: {data['peso']}KG")

    if modo == '3':
        c.drawImage("static/logo.png", 100, 385, width=80, height=30)

    c.drawImage("static/qr.png", 20, 340, width=80, height=80)

    if data['fragil']:
        c.drawImage("static/flecha_arriba.png", 200, 340, width=50, height=40)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(20, 320, "REMITENTE")
    c.setFont("Helvetica", 8)
    c.drawString(20, 308, data['remitente'])
    c.drawString(20, 295, f"DNI: {data['dni_rem']}")
    c.drawString(20, 282, f"Cel: {data['celular_rem']}")
    c.drawString(20, 270, f"{data['direccion_rem']}")
    c.drawString(20, 257, f"CP: {data['cp_rem']} - {data['ciudad_rem']} - {data['prov_rem']}")

    c.line(15, 250, 270, 250)

    if modo == '1':
        barcode = code128.Code128(numero_seguimiento, barHeight=50, barWidth=1.0, humanReadable=False)
        barcode.drawOn(c, 66, 195)
    elif modo == '3':
        barcode = code128.Code128(numero_seguimiento, barHeight=50, barWidth=1.0, humanReadable=False)
        barcode.drawOn(c, 66, 195)

    c.line(15, 190, 270, 190)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(20, 175, "DESTINATARIO")
    c.setFont("Helvetica", 8)
    c.drawString(20, 162, data['destinatario'])
    c.drawString(20, 150, f"DNI: {data['dni_dest']}")
    c.drawString(20, 137, f"Cel: {data['celular_dest']}")
    c.drawString(20, 124, data['direccion_dest'])
    c.drawString(20, 111, f"{data['ciudad_dest'].upper()} - {data['prov_dest'].upper()}")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(180, 111, f"CP: {data['cp_dest']}")

    c.line(15, 100, 270, 100)

    if data['fragil']:
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(140, 85, "■ FRÁGIL - MANIPULAR CON CUIDADO ■")
        c.drawImage("static/fragil.png", 110, 35, width=100, height=40)

    if data['observaciones']:
        c.setFont("Helvetica", 8)
        c.drawString(20, 25, f"OBS: {data['observaciones']}")

    c.save()

# --------- RUTA PRINCIPAL (sin login) --------- #
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

