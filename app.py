from flask import Flask, render_template, Response, flash, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, validators
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO, StringIO
import base64
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta'

class EstadisticasForm(FlaskForm):
    equipo = StringField('Equipo', validators=[validators.InputRequired()])         # para que el campo no este vacío.
    juegos_jugados = IntegerField('Juegos Jugados', validators=[validators.NumberRange(min=0)])
    juegos_ganados = IntegerField('Juegos Ganados', validators=[validators.NumberRange(min=0)])
    juegos_empatados = IntegerField('Juegos Empatados', validators=[validators.NumberRange(min=0)])
    rebotes = IntegerField('Rebotes', validators=[validators.NumberRange(min=0)])
    asistencias = IntegerField('Asistencias', validators=[validators.NumberRange(min=0)])
    goles = IntegerField('Goles', validators=[validators.NumberRange(min=0)])
    enviar = SubmitField('Enviar')

estadisticas = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ingresar_estadisticas', methods=['GET', 'POST'])
def ingresar_estadisticas():
    form = EstadisticasForm()
    if form.validate_on_submit():
        juegos_jugados = form.juegos_jugados.data
        juegos_ganados = form.juegos_ganados.data
        juegos_empatados = form.juegos_empatados.data
        juegos_perdidos = calcular_juegos_perdidos(form.data)

        if (juegos_ganados + juegos_empatados) > juegos_jugados:
            mensaje = 'La suma de juegos ganados y empatados no puede ser mayor que juegos jugados.'
            return render_template('ingresar_estadisticas.html', form=form, mensaje=mensaje)

        estadistica = {
            'equipo': form.equipo.data,
            'juegos_jugados': juegos_jugados,
            'juegos_ganados': juegos_ganados,
            'juegos_empatados': juegos_empatados,
            'juegos_perdidos': juegos_perdidos,
            'puntos': calcular_puntos(form.data),
            'goles': form.goles.data,
            'rebotes': form.rebotes.data,
            'asistencias': form.asistencias.data
        }
        estadisticas.append(estadistica)
        return redirect(url_for('ingresar_estadisticas'))
    return render_template('ingresar_estadisticas.html', form=form)

def calcular_puntos(estadistica):
    return (estadistica['juegos_ganados'] * 3) + estadistica['juegos_empatados']

def calcular_juegos_perdidos(estadistica):
    juegos_jugados = estadistica['juegos_jugados']
    juegos_ganados = estadistica['juegos_ganados']
    juegos_empatados = estadistica['juegos_empatados']
    return max(0, juegos_jugados - juegos_ganados - juegos_empatados)

@app.route('/ver_estadisticas')
def ver_estadisticas():
    form = EstadisticasForm()
    return render_template('ver_estadisticas.html', estadisticas=estadisticas, form=form)

@app.route('/operaciones_matrices')
def operaciones_matrices():
    if len(estadisticas) == 0:
        return render_template('operaciones_matrices.html', promedios=[], suma_total=[], efectividad_por_equipo={})

    matriz_estadisticas = np.array([[e['puntos'], e['rebotes'], e['asistencias']] for e in estadisticas])
    promedios = np.mean(matriz_estadisticas, axis=0)
    suma_total = np.sum(matriz_estadisticas, axis=0)
    efectividad_por_equipo = calcular_efectividad_por_equipo(estadisticas)
    return render_template('operaciones_matrices.html', promedios=promedios, suma_total=suma_total, efectividad_por_equipo=efectividad_por_equipo)


def calcular_efectividad_por_equipo(estadisticas):
    if not estadisticas:
        return {}
    
    nombres_equipos = [equipo['equipo'] for equipo in estadisticas]
    puntos = np.array([equipo['puntos'] for equipo in estadisticas], dtype=float)
    juegos_jugados = np.array([equipo['juegos_jugados'] for equipo in estadisticas], dtype=float)

    efectividad_por_equipo = np.nan_to_num(np.divide(puntos, juegos_jugados, out=np.zeros_like(puntos), where=juegos_jugados!=0))     # divisones por cero y convertir NaN a cero.
    efectividad_por_equipo = np.round(efectividad_por_equipo, decimals=2)

    resultado = dict(zip(nombres_equipos, efectividad_por_equipo))     # devuelve diccionario
    return resultado

@app.route('/visualizacion_datos')
def visualizacion_datos():
    form = EstadisticasForm()
    if len(estadisticas) == 0:
        return 'No hay estadísticas para visualizar'

    etiquetas = ['Puntos', 'Rebotes', 'Asistencias']
    valores_promedio = np.mean(np.array([[e['puntos'], e['rebotes'], e['asistencias']] for e in estadisticas]), axis=0)
    plt.bar(etiquetas, valores_promedio)
    plt.title('Promedio de Estadísticas')
    plt.xlabel('Categoría')
    plt.ylabel('Promedio')
    plt.grid(True)

    # Guarda la imagen en un archivo
    img_path = 'static/grafico.png'
    plt.savefig(img_path, format='png')
    plt.close()

    return render_template('visualizacion_datos.html', img_path=img_path)

@app.route('/generar_informe_pdf')
def generar_informe_pdf():
    if len(estadisticas) == 0:
        return 'No hay estadísticas para generar el informe'

    buffer = BytesIO()

    # Crea un documento PDF con reportlab
    pdf = canvas.Canvas(buffer)
    pdf.setTitle('Informe de Estadísticas Deportivas')

    # Agrega contenido al PDF
    pdf.drawString(72, 800, 'Informe de Estadísticas Deportivas')
    pdf.line(72, 790, 525, 790)

    pdf.drawString(72, 770, 'Estadísticas Ingresadas:')
    y_position = 750
    for idx, estadistica in enumerate(estadisticas, start=1):
        pdf.drawString(90, y_position, f"{idx}. Equipo: {estadistica['equipo']}, Puntos: {estadistica['puntos']}, Rebotes: {estadistica['rebotes']}, Asistencias: {estadistica['asistencias']}")
        y_position -= 15

    pdf.showPage()

    # Agrega gráfico al PDF
    img_path = 'static/grafico.png'
    pdf.drawInlineImage(img_path, 72, 400, width=400, height=200)

    # Guarda el PDF en el buffer
    pdf.save()

    # Establece la posición del buffer para leer desde el principio
    buffer.seek(0)

    # Devuelve el PDF como una respuesta del servidor
    return Response(buffer.read(), mimetype='application/pdf', headers={'Content-Disposition': 'attachment;filename=informe.pdf'})





# @app.route('/visualizacion_datos')
# def visualizacion_datos():
#     if len(estadisticas) == 0:
#         return 'No hay estadísticas para visualizar'

#     etiquetas = ['Puntos', 'Rebotes', 'Asistencias']
#     valores_promedio = np.mean(np.array([[e['puntos'], e['rebotes'], e['asistencias']] for e in estadisticas]), axis=0)
#     plt.bar(etiquetas, valores_promedio)
#     plt.title('Promedio de Estadísticas')
#     plt.xlabel('Categoría')
#     plt.ylabel('Promedio')
#     plt.grid(True)

#     img_buf = BytesIO()
#     plt.savefig(img_buf, format='png')
#     img_buf.seek(0)
#     img_data = base64.b64encode(img_buf.read()).decode('utf-8')
#     plt.close()

#     return render_template('visualizacion_datos.html', img_data=img_data)

#
if __name__ == '__main__':
    app.run(debug=True)
