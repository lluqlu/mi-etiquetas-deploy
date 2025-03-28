from flask import Flask, render_template, request, send_file, redirect, url_for, Response, session, make_response
import qrcode
import json
import os
import sqlite3
import requests  
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import portrait
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "etiqueta_secreta")

def conectar_bd():
    return sqlite3.connect("datos.db")

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



@app.route('/consultas', methods=['GET', 'POST'])
def consultas():
    codigo = request.args.get('codigo') or request.form.get('codigo')
    resultado = None
    eventos = []
    mensaje = None

    if codigo:
        conn = conectar_bd()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM envios WHERE seguimiento = ?", (codigo,))
        resultado_raw = cursor.fetchone()

        if resultado_raw:
            resultado = {
                'Seguimiento': resultado_raw['seguimiento'] or "",
                'Remitente': resultado_raw['remitente'] or "",
                'DNI Remitente': resultado_raw['dni_rem'] or "",
                'Celular Remitente': resultado_raw['cel_rem'] or "",
                'Celular Destinatario': resultado_raw['celular_dest'] or '',
                'Destinatario': resultado_raw['destinatario'] or "",
                'DNI Destinatario': resultado_raw['dni_dest'] or "",
                'CP Destino': resultado_raw['cp_dest'] or "",
                'Peso': resultado_raw['peso'] or "",
                'Frágil': bool(resultado_raw['fragil']),
                'Observaciones': resultado_raw['observaciones'] or ""
            }

            resultado['codigo_externo'] = resultado_raw['codigo_externo'] or ''

            # Ver si hay código externo y consultar AfterShip
            if resultado['codigo_externo']:
                eventos = consultar_aftership(resultado['codigo_externo'])

                # Convertir a formato esperado (dict con 'fechahora' y 'evento')
                eventos = [
                    {
                        "fechahora": e['checkpoint_time'],
                        "evento": e['message']
                    }
                    for e in eventos
                ]
            else:
                # Si no hay código externo, usar eventos locales
                cursor.execute("SELECT fechahora, evento FROM seguimiento WHERE seguimiento = ? ORDER BY id", (codigo,))
                eventos = cursor.fetchall()

            if request.method == 'POST':
                nuevo_evento = request.form.get('evento')
                if nuevo_evento:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("INSERT INTO seguimiento (seguimiento, fechahora, evento) VALUES (?, ?, ?)",
                                   (codigo, fecha_actual, nuevo_evento))
                    conn.commit()
                    eventos.append({"fechahora": fecha_actual, "evento": nuevo_evento})

        else:
            mensaje = "No se encontró ningún envío con ese código."

        conn.close()

    return render_template("consultas.html", resultado=resultado, codigo=codigo, eventos=eventos, mensaje=mensaje)



@app.route('/agregar_codigo_externo', methods=['POST'])
def agregar_codigo_externo():
    codigo = request.form.get('codigo')
    codigo_externo = request.form.get('codigo_externo')
    if codigo and codigo_externo:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE envios SET codigo_externo = ? WHERE seguimiento = ?", (codigo_externo, codigo))
        conn.commit()
        conn.close()
    return redirect(url_for('consultas', codigo=codigo))


@app.route('/historial')
@requires_auth
def historial():
    conn = conectar_bd()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM envios ORDER BY rowid DESC")
    envios = cursor.fetchall()
    conn.close()
    return render_template("historial.html", envios=envios)

@app.route('/export-csv')
@requires_auth
def export_csv():
    return send_file("static/envios.csv", as_attachment=True)

def registrar_envio(data, numero_seguimiento):
    conn = sqlite3.connect("datos.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO envios (
            seguimiento, remitente, dni_rem, cel_rem,
            destinatario, dni_dest, cp_dest, peso, fragil, observaciones,
            direccion_rem, cp_rem, ciudad_rem, prov_rem,
            direccion_dest, ciudad_dest, prov_dest, celular_dest
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        numero_seguimiento,
        data['remitente'],
        data['dni_rem'],
        data['celular_rem'],
        data['destinatario'],
        data['dni_dest'],
        data['cp_dest'],
        data['peso'],
        int(data['fragil']),
        data['observaciones'],
        data['direccion_rem'],
        data['cp_rem'],
        data['ciudad_rem'],
        data['prov_rem'],
        data['direccion_dest'],
        data['ciudad_dest'],
        data['prov_dest'],
        data['celular_dest']
    ))

    conn.commit()
    conn.close()


def generar_qr_llamada(data, modo, archivo_salida="static/qr.png"):
    if modo == '3':
        qr = qrcode.make("https://www.instagram.com/gorras.thana/")
    else:
        qr = qrcode.make(f"tel:{data['celular_dest']}")
    qr.save(archivo_salida)

def generar_etiqueta_envio(data, modo, archivo_salida="etiqueta_envio.pdf"):
    generar_qr_llamada(data, modo)
    if modo == '1':
        numero_seguimiento = get_next_tracking(data['cp_dest'])
    elif modo == '3':
        numero_seguimiento = get_next_tracking_thana(data['cp_dest'])
    else:
        numero_seguimiento = "-"
    registrar_envio(data, numero_seguimiento)

    c = canvas.Canvas(archivo_salida, pagesize=portrait((283, 425)))

    if modo in ['1', '3']:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(180, 415, f"TRACK: {numero_seguimiento}")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(200, 405, f"PESO: {data['peso']}KG")

    if modo == '3':
        c.drawImage("static/logo.png", 120, 347, width=40, height=65)

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

    if modo in ['1', '3']:
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

def get_next_tracking_thana(cp_dest):
    ruta = "static/contador_thana.json"
    if not os.path.exists(ruta):
        with open(ruta, "w") as f:
            json.dump({"secuencia": 0}, f)
    with open(ruta, "r") as f:
        datos = json.load(f)
    datos["secuencia"] += 1
    with open(ruta, "w") as f:
        json.dump(datos, f)
    return f"TH-{cp_dest}-{str(datos['secuencia']).zfill(4)}"
@app.route('/seguimiento')
def seguimiento():
    codigo = request.args.get('codigo')
    resultado = None
    eventos = []

    if codigo:
        conn = conectar_bd()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM envios WHERE seguimiento = ?", (codigo,))
        resultado_raw = cursor.fetchone()

        if resultado_raw:
            resultado = {
                'Seguimiento': resultado_raw['seguimiento'],
                'CP Remitente': resultado_raw['cp_rem'],
                'Ciudad Remitente': resultado_raw['ciudad_rem'],
                'Provincia Remitente': resultado_raw['prov_rem'],
                'CP Destino': resultado_raw['cp_dest'],
                'Ciudad Destinatario': resultado_raw['ciudad_dest'],
                'Provincia Destinatario': resultado_raw['prov_dest']
            }

            cursor.execute("SELECT fechahora, evento FROM seguimiento WHERE seguimiento = ? ORDER BY id", (codigo,))
            eventos = cursor.fetchall()

        conn.close()

    return render_template("consultas_cliente.html", resultado=resultado, codigo=codigo, eventos=eventos)


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
        session['datos'] = datos
        session['modo'] = modo
        generar_etiqueta_envio(datos, modo)
        return redirect(url_for('preview'))

    datos = session.get('datos', {})
    return render_template('formulario.html', datos=datos)

@app.route('/preview')
def preview():
    return send_file("etiqueta_envio.pdf")

def consultar_aftership(codigo_externo):
    try:
        url = f"https://api.aftership.com/v4/trackings/andreani-api/{codigo_externo}"



        headers = {
            "aftership-api-key": "asat_7e8ae2c680be478a8560f148358726da",  # Reemplazar por tu clave
            "Content-Type": "application/json"
        }
        r = requests.get(url, headers=headers)
        if r.ok:
            data = r.json()
            return data['data']['tracking']['checkpoints']
    except:
        pass
    print("Consultando AfterShip para:", codigo_externo)
    print("Respuesta:", r.status_code, r.text)

    return []
