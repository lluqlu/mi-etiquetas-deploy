from flask import Flask, render_template, request, send_file
import qrcode
import json
import os
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import portrait

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        modo = request.form.get('modo')
        datos = {
            'remitente': request.form.get('remitente'),
            'direccion_rem': request.form.get('direccion_rem'),
            'cp_rem': request.form.get('cp_rem'),
            'ciudad_rem': request.form.get('ciudad_rem'),
            'prov_rem': request.form.get('prov_rem'),
            'destinatario': request.form.get('destinatario'),
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


def generar_qr_llamada(celular_dest, archivo_salida="qr.png"):
    qr = qrcode.make(f"tel:{celular_dest}")
    qr.save(archivo_salida)

def generar_etiqueta_envio(data, modo, archivo_salida="etiqueta_envio.pdf"):
    generar_qr_llamada(data['celular_dest'])

    c = canvas.Canvas(archivo_salida, pagesize=portrait((283, 425)))

    if modo == '1':  # Courier Propio
        numero_seguimiento = f"AR-{data['cp_dest']}-01"
        c.setFont("Helvetica-Bold", 8)
        c.drawString(180, 415, f"TRACK: {numero_seguimiento}")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(200, 405, f"PESO: {data['peso']}KG")

    c.drawImage("qr.png", 20, 340, width=80, height=80)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(20, 320, "REMITENTE")
    c.setFont("Helvetica", 8)
    c.drawString(20, 308, data['remitente'])
    c.drawString(20, 295, data['direccion_rem'])
    c.drawString(20, 282, f"CP: {data['cp_rem']}")
    c.drawString(20, 270, f"{data['ciudad_rem']} - {data['prov_rem']}")

    c.line(15, 260, 270, 260)

    if modo == '1':
        barcode_draw = code128.Code128(numero_seguimiento, barHeight=30, barWidth=0.8)
        barcode_draw.drawOn(c, 50, 215)
    # SIEMPRE deja la línea divisoria (modo 1 y modo 2)
    c.line(15, 200, 270, 200)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(20, 185, "DESTINATARIO")
    c.setFont("Helvetica", 8)
    c.drawString(20, 172, data['destinatario'])
    c.drawString(20, 159, data['direccion_dest'])
    c.drawString(20, 146, data['ciudad_dest'].upper())
    c.drawString(20, 133, data['prov_dest'].upper())

    c.setFont("Helvetica-Bold", 16)
    c.drawString(180, 133, f"CP: {data['cp_dest']}")

    c.line(15, 120, 270, 120)

    if data['fragil']:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20, 100, "⚠ FRÁGIL - MANIPULAR CON CUIDADO ⚠")
        c.drawImage("fragil.png", 60, 50, width=50, height=40)
        c.drawImage("flecha_arriba.png", 140, 50, width=50, height=40)

    if data['observaciones']:
        c.setFont("Helvetica", 8)
        c.drawString(20, 30, f"OBS: {data['observaciones']}")

    c.save()

if __name__ == '__main__':
    app.run(debug=True)
