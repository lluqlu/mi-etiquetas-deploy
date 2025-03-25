from flask import Flask, render_template, request, send_file, redirect, url_for, Response, session
import qrcode
import sqlite3
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
    return redirect(url_for('login'))

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

