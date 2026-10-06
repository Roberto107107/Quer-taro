"""Private completed-agreement reports. Completion timestamps use history's UTC."""
from datetime import date, datetime, timedelta, timezone
from html import escape
from io import BytesIO
from pathlib import Path
import re
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from app import get_db


def report_period(period, reference):
    day = date.fromisoformat(reference)
    if period == 'semana':
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=7)
    elif period == 'mes':
        start = day.replace(day=1)
        end = date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)
    else:
        raise ValueError('Periodo inválido.')
    return start, end


def completed_agreements(user_id, start, end):
    return get_db().execute('''
        SELECT a.id,a.titulo,a.descripcion,a.fecha_limite,a.validado_por,
               trim(c.nombre || ' ' || c.apellidos) AS creador,
               trim(r.nombre || ' ' || r.apellidos) AS responsable,
               h.creado AS completado,h.nota AS cierre
        FROM acuerdos a
        JOIN usuarios c ON c.id=a.creador_id
        JOIN usuarios r ON r.id=a.responsable_id
        JOIN acuerdo_historial h ON h.id=(
            SELECT max(last.id) FROM acuerdo_historial last
            WHERE last.acuerdo_id=a.id AND last.estado='completado')
        WHERE a.estado='completado' AND (a.creador_id=? OR a.responsable_id=?)
          AND h.creado>=? AND h.creado<?
        ORDER BY h.creado,a.id
    ''', (user_id, user_id, start.isoformat() + 'T00:00:00', end.isoformat() + 'T00:00:00')).fetchall()


def report_pdf(user, period, start, end, items):
    output = BytesIO()
    blue = colors.HexColor('#234774')
    styles = {
        'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=21, leading=26, textColor=blue, spaceAfter=12),
        'heading': ParagraphStyle('heading', fontName='Helvetica-Bold', fontSize=12, leading=17, textColor=blue, spaceBefore=14, spaceAfter=8, keepWithNext=True),
        'body': ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=15, textColor=colors.HexColor('#344054'), spaceAfter=8),
        'meta': ParagraphStyle('meta', fontName='Helvetica', fontSize=9, leading=14, textColor=colors.HexColor('#53657a'), spaceAfter=6),
    }

    def plain(value):
        # ReportLab Paragraph understands markup. Never interpret user text as markup,
        # image sources, hyperlinks or font expressions.
        clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value or ''))
        return escape(clean).replace('\n', '<br/>')

    def para(value, style='body'):
        return Paragraph(plain(value), styles[style])

    label = 'semanal' if period == 'semana' else 'mensual'
    last_day = end - timedelta(days=1)
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=33*mm, bottomMargin=22*mm,
                            title=f'Reporte {label} de acuerdos completados', author='NEXO')
    story = [para(f'Reporte {label}', 'title'), para('Acuerdos completados', 'heading'),
             para(f'Periodo: {start:%d/%m/%Y} al {last_day:%d/%m/%Y} (UTC)', 'meta'),
             para(f'Usuario: {user["nombre"]} {user["apellidos"]}', 'meta'),
             para('Incluye los acuerdos que creaste o tienes asignados. Fecha de corte: finalización registrada en el historial.', 'meta'),
             para(f'Total completados: {len(items)}', 'heading'), Spacer(1, 4*mm)]
    if not items:
        story.append(para('No hay acuerdos completados en este periodo.'))
    for item in items:
        story.extend([
            HRFlowable(width='100%', thickness=.6, color=colors.HexColor('#dce5f1')),
            para(f'#{item["id"]:03d} · {item["titulo"]}', 'heading'),
            para(f'Responsable: {item["responsable"]}', 'meta'),
            para(f'Propuesto por: {item["creador"]}', 'meta'),
            para('Cumplimiento confirmado por quien propuso el acuerdo.' if item['validado_por'] else 'Registro histórico: sin validación independiente registrada.', 'meta'),
            para(f'Completado: {item["completado"].replace("T", " ")} UTC | Fecha de entrega: {item["fecha_limite"]}', 'meta'),
            para('Compromiso', 'heading'), para(item['descripcion']),
            para('Nota de cierre', 'heading'), para(item['cierre'] or 'Sin nota de cierre.'), Spacer(1, 4*mm),
        ])
    logo = Path(current_app.static_folder) / 'img' / 'logo.png'
    generated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')

    def page_frame(canvas, document):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(blue)
        canvas.setFont('Helvetica-Bold', 13)
        canvas.drawString(20*mm, height - 20*mm, 'NEXO')
        canvas.setFont('Helvetica', 8)
        canvas.drawString(20*mm, height - 25*mm, 'Comunicación institucional · Reporte personal')
        if logo.is_file():
            canvas.drawImage(str(logo), width - 42*mm, height - 30*mm, 22*mm, 22*mm, preserveAspectRatio=True, mask='auto')
        canvas.setStrokeColor(colors.HexColor('#dce5f1'))
        canvas.line(20*mm, 17*mm, width - 20*mm, 17*mm)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(20*mm, 12*mm, f'Generado: {generated}')
        canvas.drawRightString(width - 20*mm, 12*mm, f'Página {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
    output.seek(0)
    return output
