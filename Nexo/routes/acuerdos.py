from datetime import date
from flask import abort, flash, g, redirect, render_template, request, url_for
from app import get_db
from app.acuerdo import STATES, QUERY, actions, decorate
from app.usuario import login_required, admin_required


def private_agreement(agreement_id):
    row = get_db().execute(QUERY + ' WHERE a.id=? AND (a.creador_id=? OR a.responsable_id=?)',
                           (agreement_id, g.usuario['id'], g.usuario['id'])).fetchone()
    if row is None:
        abort(404, 'Acuerdo no disponible.')
    return decorate(row)


def register(app):
    @app.get('/acuerdos')
    @login_required
    def acuerdos():
        items = [decorate(row) for row in get_db().execute(
            QUERY + ' WHERE a.creador_id=? OR a.responsable_id=? ORDER BY a.fecha_limite,a.id DESC',
            (g.usuario['id'], g.usuario['id']))]
        counts = {state: sum(item['estado'] == state for item in items) for state in STATES}
        overdue = sum(item['vencido'] for item in items)
        state = request.args.get('estado', '')
        if state == 'activos':
            items = [item for item in items if item['estado'] in ('pendiente', 'en_proceso')]
        elif state:
            items = [item for item in items if (item['vencido'] if state == 'vencidos' else item['estado'] == state)]
        return render_template('acuerdos/index.html', acuerdos=items, counts=counts,
                               vencidos=overdue, estados=STATES)

    @app.route('/mensajes/<int:message_id>/acuerdo', methods=['GET', 'POST'])
    @login_required
    def crear_acuerdo(message_id):
        message = get_db().execute('SELECT * FROM mensajes WHERE id=? AND (remitente_id=? OR destinatario_id=?)',
                                  (message_id, g.usuario['id'], g.usuario['id'])).fetchone()
        if message is None:
            abort(404, 'Mensaje no disponible.')
        people = get_db().execute('SELECT id,nombre,apellidos FROM usuarios WHERE id IN (?,?) AND activo=1 AND verificado=1',
                                 (message['remitente_id'], message['destinatario_id'])).fetchall()
        if request.method == 'POST':
            title = request.form.get('titulo', '').strip()
            description = request.form.get('descripcion', '').strip()
            responsible = request.form.get('responsable_id', type=int)
            try:
                deadline = date.fromisoformat(request.form.get('fecha_limite', '')).isoformat()
                if deadline < date.today().isoformat():
                    raise ValueError('La fecha límite no puede estar en el pasado.')
                if not title or len(title) > 200 or not description or len(description) > 5000:
                    raise ValueError('Escribe un título (hasta 200 caracteres) y una descripción (hasta 5000).')
                if responsible not in [person['id'] for person in people]:
                    raise ValueError('El responsable debe ser un participante activo de esta conversación.')
            except ValueError as exc:
                flash(str(exc) if str(exc) and not str(exc).startswith('Invalid') else 'Selecciona una fecha válida.', 'error')
            else:
                db = get_db()
                with db:
                    cursor = db.execute('INSERT INTO acuerdos(mensaje_id,creador_id,responsable_id,titulo,descripcion,fecha_limite) VALUES(?,?,?,?,?,?)',
                                        (message_id, g.usuario['id'], responsible, title, description, deadline))
                    agreement_id = cursor.lastrowid
                    db.execute('INSERT INTO acuerdo_historial(acuerdo_id,actor_id,estado,nota) VALUES(?,?,?,?)',
                               (agreement_id, g.usuario['id'], 'propuesto', 'Acuerdo propuesto desde una conversación.'))
                flash('Acuerdo enviado para aceptación.', 'success')
                return redirect(url_for('detalle_acuerdo', agreement_id=agreement_id))
        return render_template('acuerdos/crear.html', mensaje=message, personas=people, hoy=date.today().isoformat())

    @app.route('/acuerdos/<int:agreement_id>', methods=['GET', 'POST'])
    @login_required
    def detalle_acuerdo(agreement_id):
        item = private_agreement(agreement_id)
        if request.method == 'POST':
            target = request.form.get('estado', '')
            note = request.form.get('nota', '').strip()
            if target not in dict(actions(item, g.usuario['id'])):
                abort(403, 'No puedes realizar este cambio de estado.')
            if len(note) > 5000 or (target in ('completado', 'rechazado', 'cancelado') and not note):
                flash('Agrega una nota de cierre o motivo (hasta 5000 caracteres).', 'error')
            else:
                db = get_db()
                with db:
                    result = db.execute('UPDATE acuerdos SET estado=? WHERE id=? AND estado=?', (target, agreement_id, item['estado']))
                    if result.rowcount != 1:
                        abort(409, 'El acuerdo cambió. Recarga la página.')
                    db.execute('INSERT INTO acuerdo_historial(acuerdo_id,actor_id,estado,nota) VALUES(?,?,?,?)',
                               (agreement_id, g.usuario['id'], target, note))
                flash('Acuerdo actualizado.', 'success')
                return redirect(url_for('detalle_acuerdo', agreement_id=agreement_id))
        history = get_db().execute('SELECT h.*,u.nombre FROM acuerdo_historial h JOIN usuarios u ON u.id=h.actor_id WHERE acuerdo_id=? ORDER BY h.id DESC', (agreement_id,)).fetchall()
        message = get_db().execute('SELECT * FROM mensajes WHERE id=?', (item['mensaje_id'],)).fetchone()
        other_id = message['destinatario_id'] if message['remitente_id'] == g.usuario['id'] else message['remitente_id']
        return render_template('acuerdos/detalle.html', acuerdo=item, historial=history, mensaje=message,
                               other_id=other_id, estados=STATES, acciones=actions(item, g.usuario['id']))

    @app.get('/admin/acuerdos')
    @admin_required
    def admin_acuerdos():
        # Only aggregate metrics: no titles, message text, participants or private notes.
        rows = get_db().execute("""SELECT estado,count(*) AS total,
            sum(CASE WHEN fecha_limite<? AND estado IN ('propuesto','pendiente','en_proceso') THEN 1 ELSE 0 END) AS vencidos
            FROM acuerdos GROUP BY estado""", (date.today().isoformat(),)).fetchall()
        counts = {state: 0 for state in STATES}
        for row in rows:
            counts[row['estado']] = row['total']
        total = sum(counts.values())
        return render_template('acuerdos/admin.html', estados=STATES, counts=counts, total=total,
                               vencidos=sum(row['vencidos'] for row in rows),
                               porcentaje=round(100 * counts['completado'] / total) if total else 0)
