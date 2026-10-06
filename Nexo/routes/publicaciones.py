from datetime import date, datetime
from flask import abort, flash, g, redirect, render_template, url_for, send_from_directory
from app import get_db
from app.publicacion import visible_publications
from app.usuario import login_required
from app.imagen import image_folder


def recent_content(user_id):
    db = get_db()
    seen_posts = {r[0] for r in db.execute('SELECT publicacion_id FROM enterados_publicaciones WHERE usuario_id=?', (user_id,))}
    seen_calls = {r[0] for r in db.execute('SELECT convocatoria_id FROM enterados_convocatorias WHERE usuario_id=?', (user_id,))}
    seen_docs = {r[0] for r in db.execute('SELECT documento_id FROM enterados_documentos WHERE usuario_id=?', (user_id,))}
    applications = {r[0]: r[1] for r in db.execute('SELECT convocatoria_id,estado FROM postulaciones WHERE usuario_id=?', (user_id,))}
    items = []
    for row in visible_publications():
        item = dict(row)
        item.update(clase='publicacion', enterado=item['id'] in seen_posts,
                    orden=item['fecha'] + 'T' + item['creado'][11:])
        items.append(item)
    for row in db.execute('''SELECT c.*, u.nombre AS autor FROM convocatorias c
                            JOIN usuarios u ON u.id=c.autor_id WHERE c.archivado=0 AND c.fin>=?''',
                          (datetime.now().isoformat(timespec='minutes'),)):
        item = dict(row)
        item.update(clase='convocatoria', tipo='Convocatoria', fecha=item['creado'][:10],
                    enterado=item['id'] in seen_calls, orden=item['creado'], postulado=item['id'] in applications,
                    estado_postulacion=applications.get(item['id']))
        items.append(item)
    for row in db.execute('SELECT d.*, u.nombre AS autor FROM documentos d JOIN usuarios u ON u.id=d.autor_id WHERE d.archivado=0'):
        item = dict(row)
        item.update(clase='documento', tipo='Documento', titulo=item['nombre'], contenido='',
                    fecha=item['creado'][:10], orden=item['creado'], enterado=item['id'] in seen_docs)
        items.append(item)
    return sorted(items, key=lambda item: (item['orden'], item['id']), reverse=True)[:12]


def register(app):
    @app.post('/convocatorias/<int:record_id>/postular')
    @login_required
    def postular_convocatoria(record_id):
        if g.usuario['rol'] != 'usuario':
            abort(403)
        db = get_db()
        item = db.execute('SELECT id,fin FROM convocatorias WHERE archivado=0 AND id=?', (record_id,)).fetchone()
        if item is None:
            abort(404, 'Convocatoria no encontrada.')
        now = datetime.now().isoformat(timespec='minutes')
        if item['fin'] < now:
            abort(409, 'La convocatoria ya cerró y no admite postulaciones.')
        result = db.execute('''INSERT OR IGNORE INTO postulaciones(usuario_id,convocatoria_id)
            SELECT ?,id FROM convocatorias WHERE archivado=0 AND id=? AND fin>=?''', (g.usuario['id'], record_id, now))
        db.commit()
        flash('Tu postulación quedó registrada.' if result.rowcount else 'Ya tienes una postulación registrada.', 'success')
        return redirect(url_for('inicio', _anchor=f'convocatoria-{record_id}'))

    @app.get('/contenido/<tipo>/<int:record_id>/imagen')
    @login_required
    def imagen_contenido(tipo, record_id):
        table = {'publicacion': 'publicaciones', 'convocatoria': 'convocatorias'}.get(tipo)
        if table is None:
            abort(404)
        item = get_db().execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone()
        if not item or not item['imagen']:
            abort(404)
        if g.usuario['rol'] != 'admin':
            if item['archivado']:
                abort(404)
            if tipo == 'publicacion':
                today = date.today().isoformat()
                if item['estado'] != 'published' or item['fecha'] > today or (item['vencimiento'] and item['vencimiento'] < today):
                    abort(404)
            elif item['fin'] < datetime.now().isoformat(timespec='minutes'):
                abort(404)
        response = send_from_directory(image_folder(), item['imagen'], mimetype='image/webp')
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/inicio')
    @login_required
    def inicio():
        if g.usuario['rol'] == 'admin':
            return redirect(url_for('admin'))
        return render_template('main/inicio.html', novedades=recent_content(g.usuario['id']))

    @app.post('/enterado/<tipo>/<int:record_id>')
    @login_required
    def enterado(tipo, record_id):
        if g.usuario['rol'] != 'usuario':
            abort(403)
        db = get_db()
        if tipo == 'publicacion':
            today = date.today().isoformat()
            row = db.execute("""SELECT id FROM publicaciones WHERE archivado=0 AND id=? AND estado='published'
                AND fecha<=? AND (vencimiento IS NULL OR vencimiento>=?)""", (record_id, today, today)).fetchone()
            table, column = 'enterados_publicaciones', 'publicacion_id'
        elif tipo == 'convocatoria':
            row = db.execute('SELECT id FROM convocatorias WHERE archivado=0 AND id=? AND fin>=?',
                             (record_id, datetime.now().isoformat(timespec='minutes'))).fetchone()
            table, column = 'enterados_convocatorias', 'convocatoria_id'
        elif tipo == 'documento':
            row = db.execute('SELECT id FROM documentos WHERE archivado=0 AND id=?', (record_id,)).fetchone()
            table, column = 'enterados_documentos', 'documento_id'
        else:
            abort(404)
        if row is None:
            abort(404, 'Contenido no disponible.')
        # Identifiers above are constants, never request-provided SQL.
        db.execute(f'INSERT OR IGNORE INTO {table}(usuario_id,{column}) VALUES(?,?)', (g.usuario['id'], record_id))
        db.commit()
        flash('Confirmación de enterado registrada.', 'success')
        return redirect(url_for('inicio'))
