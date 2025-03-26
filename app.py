from flask import Flask, render_template, request, send_file, redirect, url_for, Response, session, make_response
import qrcode
import json
import os
import sqlite3
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
@requires_auth
def consultas():
    codigo = request.args.get('codigo') or request.form.get('codigo')
    resultado = None
    eventos = []

    if codigo:
        conn = conectar_bd()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM envios WHERE seguimiento = ?", (codigo,))
        resultado = cursor.fetchone()

        cursor.execute("SELECT fechahora, evento FROM seguimiento WHERE seguimiento = ? ORDER BY id", (codigo,))
        eventos = cursor.fetchall()

        if request.method == 'POST' and resultado:
            nuevo_evento = request.form.get('evento')
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO seguimiento (seguimiento, fechahora, evento) VALUES (?, ?, ?)",
                           (codigo, fecha_actual, nuevo_evento))
            conn.commit()
            eventos.append({"fechahora": fecha_actual, "evento": nuevo_evento})

        conn.close()

    return render_template("consultas.html", resultado=resultado, codigo=codigo, eventos=eventos)

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
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO envios (seguimiento, remitente, dni_rem, cel_rem, destinatario, dni_dest,
                            cp_dest, peso, fragil, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        data['observaciones']
    ))
    conn.commit()
    conn.close()

# ... (el resto del código permanece igual como lo tenías)

