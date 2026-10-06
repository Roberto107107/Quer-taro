"""Administrative aggregates shared by the dashboard and its PDF export."""
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from app import get_db
from app.acuerdo import STATES
from app.reporte import report_period


def dashboard_period(period, reference):
    if period == 'anio':
        day = date.fromisoformat(reference)
        return date(day.year, 1, 1), date(day.year + 1, 1, 1)
    return report_period(period, reference)


def statistics(period, start, end):
    db = get_db()
    bounds = (start.isoformat() + 'T00:00:00', end.isoformat() + 'T00:00:00')
    metrics = []
    # Identifiers are internal constants; all date bounds are bound parameters.
    for table, label in [('usuarios', 'Usuarios registrados'), ('publicaciones', 'Publicaciones creadas'),
                         ('convocatorias', 'Convocatorias creadas'), ('documentos', 'Documentos cargados'),
                         ('mensajes', 'Mensajes enviados'), ('postulaciones', 'Postulaciones recibidas')]:
        total = db.execute(f'SELECT count(*) FROM {table} WHERE creado>=? AND creado<?', bounds).fetchone()[0]
        metrics.append({'label': label, 'value': total})
    completed = db.execute('''SELECT h.creado FROM acuerdo_historial h
        JOIN acuerdos a ON a.id=h.acuerdo_id WHERE a.estado='completado'
        AND h.id=(SELECT max(x.id) FROM acuerdo_historial x WHERE x.acuerdo_id=a.id AND x.estado='completado')
        AND h.creado>=? AND h.creado<?''', bounds).fetchall()
    metrics.append({'label': 'Acuerdos completados', 'value': len(completed)})
    acknowledgments = 0
    for table in ('enterados_publicaciones', 'enterados_convocatorias', 'enterados_documentos'):
        acknowledgments += db.execute(f'SELECT count(*) FROM {table} WHERE creado>=? AND creado<?', bounds).fetchone()[0]
    metrics.append({'label': 'Confirmaciones de enterado', 'value': acknowledgments})
    agreement_counts = dict(db.execute('SELECT estado,count(*) FROM acuerdos GROUP BY estado').fetchall())
    states = [{'label': label, 'value': agreement_counts.get(state, 0)} for state, label in STATES.items()]
    application_counts = dict(db.execute('''SELECT estado,count(*) FROM postulaciones
        WHERE creado>=? AND creado<? GROUP BY estado''', bounds).fetchall())
    applications = [{'label': label, 'value': application_counts.get(state, 0)}
                    for state, label in [('pendiente', 'Pendientes'), ('aceptada', 'Aceptadas'), ('rechazada', 'Rechazadas')]]
    monthly = period == 'anio'
    days = [date(start.year, month, 1) for month in range(1, 13)] if monthly else [start + timedelta(days=n) for n in range((end-start).days)]
    timeline = {day.isoformat()[:7 if monthly else 10]: {'label': day.strftime('%m/%Y' if monthly else '%d/%m'), 'value': 0} for day in days}
    for row in completed:
        timeline[row['creado'][:7 if monthly else 10]]['value'] += 1
    snapshot = [
        {'label': 'Usuarios activos y verificados', 'value': db.execute('SELECT count(*) FROM usuarios WHERE activo=1 AND verificado=1').fetchone()[0]},
        {'label': 'Cuentas pendientes de verificación', 'value': db.execute('SELECT count(*) FROM usuarios WHERE verificado=0').fetchone()[0]},
        {'label': 'Acuerdos abiertos vencidos', 'value': db.execute("SELECT count(*) FROM acuerdos WHERE estado IN ('propuesto','pendiente','en_proceso','correcciones') AND fecha_limite<?", (date.today().isoformat(),)).fetchone()[0]},
        {'label': 'Postulaciones pendientes de resolver', 'value': db.execute("SELECT count(*) FROM postulaciones WHERE estado='pendiente'").fetchone()[0]},
    ]
    return {'metrics': metrics, 'states': states, 'applications': applications, 'timeline': list(timeline.values()),
            'snapshot': snapshot, 'start': start, 'last': end - timedelta(days=1),
            'period': period, 'period_label': {'semana': 'Semanal', 'mes': 'Mensual', 'anio': 'Anual'}[period],
            'generated': datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}


def statistics_pdf(data):
    output = BytesIO()
    styles = getSampleStyleSheet()
    for name in ('Title', 'Heading2'):
        styles[name].textColor = colors.HexColor('#234774')
    def p(text, style='Normal'):
        # All text below is application-owned labels or formatted numbers/dates.
        return Paragraph(text, styles[style])
    def table(rows, headings=('Indicador', 'Total')):
        result = Table([list(headings)] + [[p(row['label']), str(row['value'])] for row in rows], colWidths=[135*mm, 30*mm], repeatRows=1)
        result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#234774')),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white), ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#eef3fa')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(1,1),(1,-1),'RIGHT'),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        return result
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 160, 25, 280, 145
    chart.data = [[row['value'] for row in data['metrics']]]
    chart.categoryAxis.categoryNames = [row['label'] for row in data['metrics']]
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(1, max(row['value'] for row in data['metrics']))
    chart.valueAxis.valueStep = max(1, (chart.valueAxis.valueMax + 4)//5)
    chart.bars[0].fillColor = colors.HexColor('#3c79c7')
    chart.bars[0].strokeColor = None
    drawing = Drawing(470, 185)
    drawing.add(chart)
    story = [p('NEXO · Reporte administrativo', 'Title'), p(data['period_label'], 'Heading2'),
             p(f"Del {data['start']:%d/%m/%Y} al {data['last']:%d/%m/%Y} · Fechas de actividad en UTC"),
             p('Información agregada, sin mensajes, títulos de acuerdos ni datos personales.'), Spacer(1, 12),
             table(data['metrics']), Spacer(1, 12), drawing,
             p('Publicaciones creadas incluye borradores. Enterados son confirmaciones, no visitas.'), PageBreak(),
             p('Situación actual al generar el reporte', 'Heading2'), p(data['generated']), Spacer(1, 10), table(data['snapshot']),
             p('Acuerdos: estado actual de todos los registros', 'Heading2'), table(data['states'], ('Estado', 'Total')),
             p('Postulaciones recibidas en el periodo: estado actual', 'Heading2'), table(data['applications'], ('Estado', 'Total')),
             PageBreak(), p('Evolución de acuerdos completados', 'Heading2'),
             p('Por mes en el reporte anual; por día en los reportes semanal y mensual. Se usa el evento de finalización del historial.'),
             Spacer(1, 12), table(data['timeline'], ('Fecha (UTC)', 'Completados')),
             Spacer(1, 12), p('Los totales reflejan los registros que se conservan. El archivado conserva los datos para los reportes históricos. La situación actual no reconstruye estados pasados.')]
    logo = Path(current_app.static_folder) / 'img/logo.png'
    def page(canvas, doc):
        canvas.saveState()
        if logo.is_file():
            canvas.drawImage(str(logo), 170*mm, 273*mm, 20*mm, 20*mm, preserveAspectRatio=True, mask='auto')
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#53657a'))
        canvas.drawString(20*mm, 12*mm, 'Generado: ' + data['generated'])
        canvas.drawRightString(190*mm, 12*mm, f'Página {doc.page}')
        canvas.restoreState()
    SimpleDocTemplate(output, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
        topMargin=28*mm, bottomMargin=22*mm, title='NEXO - Reporte administrativo', author='NEXO').build(story, onFirstPage=page, onLaterPages=page)
    output.seek(0)
    return output
