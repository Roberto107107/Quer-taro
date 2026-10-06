from flask import abort, flash, g, redirect, render_template, request, url_for
from app import get_db
from app.usuario import login_required, admin_required
from app.seguimiento import audit, notify_due

CONTENT = {'publicacion': 'publicaciones', 'convocatoria': 'convocatorias', 'documento': 'documentos'}

def register(app):
    @app.get('/notificaciones')
    @login_required
    def notificaciones():
        notify_due(g.usuario['id'])
        page = max(1,request.args.get('pagina',1,type=int))
        rows=get_db().execute('SELECT * FROM notificaciones WHERE usuario_id=? ORDER BY id DESC LIMIT 51 OFFSET ?',
            (g.usuario['id'],(page-1)*50)).fetchall()
        return render_template('notificaciones.html',avisos=rows[:50],pagina=page,mas=len(rows)>50)

    @app.post('/notificaciones/<int:notice_id>/leida')
    @login_required
    def notificacion_leida(notice_id):
        db=get_db()
        result=db.execute('UPDATE notificaciones SET leida=1 WHERE id=? AND usuario_id=?',(notice_id,g.usuario['id']))
        if not result.rowcount:
            abort(404)
        db.commit()
        return redirect(url_for('notificaciones'))

    @app.get('/admin/historial')
    @admin_required
    def admin_historial():
        page=max(1,request.args.get('pagina',1,type=int))
        rows=get_db().execute('''SELECT h.*,u.nombre AS actor FROM auditoria h
            LEFT JOIN usuarios u ON u.id=h.actor_id ORDER BY h.id DESC LIMIT 51 OFFSET ?''',((page-1)*50,)).fetchall()
        return render_template('admin/historial.html',eventos=rows[:50],pagina=page,mas=len(rows)>50)

    @app.get('/admin/archivo')
    @admin_required
    def admin_archivo():
        page=max(1,request.args.get('pagina',1,type=int))
        rows=get_db().execute('''SELECT 'publicacion' AS tipo,id,titulo FROM publicaciones WHERE archivado=1
            UNION ALL SELECT 'convocatoria',id,titulo FROM convocatorias WHERE archivado=1
            UNION ALL SELECT 'documento',id,nombre FROM documentos WHERE archivado=1
            ORDER BY tipo,id LIMIT 51 OFFSET ?''',((page-1)*50,)).fetchall()
        return render_template('admin/archivo.html',registros=rows[:50],pagina=page,mas=len(rows)>50)

    @app.post('/admin/archivo/<tipo>/<int:record_id>/restaurar')
    @admin_required
    def restaurar_archivo(tipo,record_id):
        table=CONTENT.get(tipo)
        if not table:
            abort(404)
        db=get_db()
        with db:
            result=db.execute(f'UPDATE {table} SET archivado=0 WHERE id=? AND archivado=1',(record_id,))
            if not result.rowcount:
                abort(404)
            audit('restaurar',tipo,record_id)
        flash('Registro restaurado. Se conservan sus fechas y estado originales.','success')
        return redirect(url_for('admin_archivo'))
