from datetime import date, datetime, timezone
from pathlib import Path
import secrets
from flask import abort, flash, g, redirect, render_template, request, send_from_directory, send_file, url_for, current_app
from werkzeug.utils import secure_filename
from app import get_db
from app.convocatoria import list_calls
from app.usuario import admin_required, login_required
from app.imagen import save_image, remove_image
from app.documento import validate_document
from app.seguimiento import audit

def required(name, maximum=200):
    value = request.form.get(name, "").strip()
    if not value or len(value) > maximum:
        raise ValueError(f"El campo {name} es obligatorio y admite hasta {maximum} caracteres.")
    return value

def record(table, record_id):
    # table is supplied only by the literal route registrations below.
    row = get_db().execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone()
    if row is None:
        abort(404, "Registro no encontrado.")
    return row

def register(app):
    def selected_statistics():
        from app.estadisticas import dashboard_period, statistics
        period = request.args.get('periodo', 'mes')
        reference = request.args.get('fecha', datetime.now(timezone.utc).date().isoformat())
        try:
            start, end = dashboard_period(period, reference)
        except (ValueError, OverflowError):
            abort(400, 'Selecciona semana, mes o año y una fecha válida.')
        return statistics(period, start, end), reference

    @app.get('/admin/reporte.pdf')
    @admin_required
    def admin_reporte():
        from app.estadisticas import statistics_pdf
        data, _ = selected_statistics()
        return send_file(statistics_pdf(data), mimetype='application/pdf', as_attachment=True,
                         download_name=f"nexo-administracion-{data['period']}-{data['start'].isoformat()}.pdf", max_age=0)

    content_types = {
        'publicacion': ('publicaciones', 'enterados_publicaciones', 'publicacion_id', 'admin_publicaciones'),
        'convocatoria': ('convocatorias', 'enterados_convocatorias', 'convocatoria_id', 'admin_convocatorias'),
        'documento': ('documentos', 'enterados_documentos', 'documento_id', 'documentos'),
    }

    @app.context_processor
    def acknowledgment_counts():
        if not g.get('usuario') or g.usuario['rol'] != 'admin':
            return {}
        counts = {}
        for kind, (_, table, column, _) in content_types.items():
            counts[kind] = {row[0]: row[1] for row in get_db().execute(
                f'SELECT {column}, count(*) FROM {table} GROUP BY {column}')}
        applications = {r[0]: r[1] for r in get_db().execute('SELECT convocatoria_id,count(*) FROM postulaciones GROUP BY convocatoria_id')}
        return {'conteos_enterados': counts, 'conteos_postulantes': applications}

    @app.get('/admin/convocatorias/<int:record_id>/postulantes')
    @admin_required
    def admin_postulantes(record_id):
        item = record('convocatorias', record_id)
        applicants = get_db().execute('''SELECT u.nombre,u.apellidos,u.correo,u.area,p.creado,p.usuario_id,p.estado
            FROM postulaciones p JOIN usuarios u ON u.id=p.usuario_id
            WHERE p.convocatoria_id=? ORDER BY p.creado DESC,u.id''', (record_id,)).fetchall()
        return render_template('admin/postulantes.html', convocatoria=item, postulantes=applicants)

    @app.post('/admin/convocatorias/<int:record_id>/postulantes/<int:user_id>/resolver')
    @admin_required
    def resolver_postulacion(record_id, user_id):
        item = record('convocatorias', record_id)
        status = request.form.get('estado')
        if status not in ('aceptada', 'rechazada'):
            abort(400, 'Selecciona aceptar o rechazar.')
        db = get_db()
        with db:
            result = db.execute('''UPDATE postulaciones SET estado=?,revisado_por=?,
                revisado=strftime('%Y-%m-%dT%H:%M:%S','now')
                WHERE convocatoria_id=? AND usuario_id=? AND estado='pendiente' ''',
                (status, g.usuario['id'], record_id, user_id))
            if not result.rowcount:
                existing = db.execute('SELECT estado FROM postulaciones WHERE convocatoria_id=? AND usuario_id=?',
                                      (record_id, user_id)).fetchone()
                if existing is None:
                    abort(404, 'Postulación no encontrada.')
                abort(409, 'Esta postulación ya fue resuelta.')
            db.execute('INSERT INTO mensajes(remitente_id,destinatario_id,contenido) VALUES(?,?,?)',
                       (g.usuario['id'], user_id, f'Tu postulación fue {status}. Convocatoria: {item["titulo"]}.'))
            audit('resolver postulación','convocatoria',record_id,f'Usuario #{user_id}: {status}')
        flash('Decisión guardada. El usuario recibió un mensaje en Mensajes.', 'success')
        return redirect(url_for('admin_postulantes', record_id=record_id))

    @app.get('/admin/enterados/<tipo>/<int:record_id>')
    @admin_required
    def admin_enterados(tipo, record_id):
        if tipo not in content_types:
            abort(404)
        table, acknowledgments, column, back = content_types[tipo]
        item = record(table, record_id)
        users = get_db().execute(f'''SELECT u.nombre, u.apellidos, u.correo, u.area,
            e.creado AS confirmado FROM {acknowledgments} e
            JOIN usuarios u ON u.id=e.usuario_id WHERE e.{column}=?
            ORDER BY e.creado DESC,u.id''', (record_id,)).fetchall()
        return render_template('admin/enterados.html', titulo=item['nombre'] if tipo == 'documento' else item['titulo'],
                               enterados=users, volver=back)

    @app.get("/admin")
    @admin_required
    def admin():
        analytics, reference = selected_statistics()
        db = get_db()
        calls = list_calls()
        stats = {
            "usuarios": db.execute("SELECT count(*) FROM usuarios").fetchone()[0],
            "publicaciones": db.execute("SELECT count(*) FROM publicaciones").fetchone()[0],
            "convocatorias": sum(item["estado"] == "Vigente" for item in calls),
            "mensajes": db.execute("SELECT count(*) FROM mensajes WHERE date(creado)=date('now')").fetchone()[0],
        }
        recent = db.execute("SELECT * FROM publicaciones WHERE archivado=0 ORDER BY id DESC LIMIT 5").fetchall()
        return render_template("admin/dashboard.html", stats=stats, publicaciones=recent, convocatorias=calls[:5], analytics=analytics, report_reference=reference)

    @app.route("/admin/publicaciones", methods=["GET", "POST"])
    @admin_required
    def admin_publicaciones():
        edit = request.args.get("editar", type=int)
        item = record("publicaciones", edit) if edit else None
        if request.method == "POST":
            new_image = None
            try:
                title, content, kind = required("titulo"), required("contenido", 20000), required("tipo")
                status = required("estado")
                if kind not in ("Aviso", "Comunicado", "Evento", "Información general") or status not in ("published", "draft"):
                    raise ValueError("Tipo o estado no válido.")
                start = date.fromisoformat(required("fecha")).isoformat()
                end = request.form.get("vencimiento", "") or None
                if end:
                    end = date.fromisoformat(end).isoformat()
                    if end < start:
                        raise ValueError("El vencimiento no puede ser anterior a la publicación.")
                new_image = save_image(request.files.get('imagen'))
                image = new_image or (item['imagen'] if item else None)
                if request.form.get('quitar_imagen') == '1' and not new_image:
                    image = None
                values = (title, content, kind, status, start, end, image)
                if item:
                    get_db().execute("UPDATE publicaciones SET titulo=?,contenido=?,tipo=?,estado=?,fecha=?,vencimiento=?,imagen=? WHERE id=?",
                                     (*values, item["id"]))
                else:
                    cursor = get_db().execute("INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,vencimiento,imagen,autor_id) VALUES(?,?,?,?,?,?,?,?)",
                                     (*values, g.usuario["id"]))
                audit('editar' if item else 'crear','publicacion',item['id'] if item else cursor.lastrowid)
                get_db().commit()
                if item and item['imagen'] != image:
                    remove_image(item['imagen'])
                flash("Publicación guardada.", "success")
                return redirect(url_for("admin_publicaciones"))
            except ValueError as exc:
                flash(str(exc), "error")
            except Exception:
                get_db().rollback()
                remove_image(new_image)
                raise
        items = get_db().execute("SELECT * FROM publicaciones WHERE archivado=0 ORDER BY id DESC").fetchall()
        return render_template("admin/publicaciones.html", publicaciones=items, item=item, hoy=date.today().isoformat())

    @app.post("/admin/publicaciones/<int:record_id>/eliminar")
    @admin_required
    def eliminar_publicacion(record_id):
        item = record("publicaciones", record_id)
        get_db().execute("UPDATE publicaciones SET archivado=1 WHERE id=?", (record_id,))
        audit('archivar','publicacion',record_id)
        get_db().commit()
        flash("Publicación archivada.", "success")
        return redirect(url_for("admin_publicaciones"))

    @app.route("/admin/convocatorias", methods=["GET", "POST"])
    @admin_required
    def admin_convocatorias():
        edit = request.args.get("editar", type=int)
        item = record("convocatorias", edit) if edit else None
        if request.method == "POST":
            new_image = None
            try:
                title, content, area, place = required("titulo"), required("contenido", 20000), required("area"), required("lugar")
                start = datetime.fromisoformat(required("inicio"))
                end = datetime.fromisoformat(required("fin"))
                if start.tzinfo or end.tzinfo:
                    raise ValueError("Usa fechas en la hora local de la institución.")
                if end < start:
                    raise ValueError("El cierre no puede ser anterior al inicio.")
                new_image = save_image(request.files.get('imagen'))
                image = new_image or (item['imagen'] if item else None)
                if request.form.get('quitar_imagen') == '1' and not new_image:
                    image = None
                values = (title, content, area, place, start.isoformat(timespec="minutes"), end.isoformat(timespec="minutes"), image)
                if item:
                    get_db().execute("UPDATE convocatorias SET titulo=?,contenido=?,area=?,lugar=?,inicio=?,fin=?,imagen=? WHERE id=?",
                                     (*values, item["id"]))
                else:
                    cursor = get_db().execute("INSERT INTO convocatorias(titulo,contenido,area,lugar,inicio,fin,imagen,autor_id) VALUES(?,?,?,?,?,?,?,?)",
                                     (*values, g.usuario["id"]))
                audit('editar' if item else 'crear','convocatoria',item['id'] if item else cursor.lastrowid)
                get_db().commit()
                if item and item['imagen'] != image:
                    remove_image(item['imagen'])
                flash("Convocatoria guardada.", "success")
                return redirect(url_for("admin_convocatorias"))
            except ValueError as exc:
                flash(str(exc), "error")
            except Exception:
                get_db().rollback()
                remove_image(new_image)
                raise
        return render_template("admin/convocatorias.html", convocatorias=list_calls(), item=item)

    @app.post("/admin/convocatorias/<int:record_id>/eliminar")
    @admin_required
    def eliminar_convocatoria(record_id):
        item = record("convocatorias", record_id)
        get_db().execute("UPDATE convocatorias SET archivado=1 WHERE id=?", (record_id,))
        audit('archivar','convocatoria',record_id)
        get_db().commit()
        flash("Convocatoria archivada.", "success")
        return redirect(url_for("admin_convocatorias"))

    @app.route("/admin/usuarios", methods=["GET", "POST"])
    @admin_required
    def admin_usuarios():
        if request.method == "POST":
            user_id = request.form.get("usuario_id", type=int)
            target_user = record("usuarios", user_id)
            role = request.form.get("rol")
            active = int(request.form.get("activo") == "1")
            verified = int(request.form.get("verificado") == "1")
            if role not in ("usuario", "admin"):
                abort(400, "Rol inválido.")
            if user_id == g.usuario["id"] and (role != "admin" or not active or not verified):
                flash("No puedes quitarte tu propio acceso de administración.", "error")
            else:
                get_db().execute("UPDATE usuarios SET rol=?,activo=?,verificado=? WHERE id=?",
                                 (role, active, verified, user_id))
                if not active or not verified or role != target_user['rol']:
                    get_db().execute('DELETE FROM auth_sessions WHERE usuario_id=?', (user_id,))
                audit('actualizar permisos','usuario',user_id,f"Rol {target_user['rol']} → {role}; activo {target_user['activo']} → {active}; verificado {target_user['verificado']} → {verified}")
                get_db().commit()
                flash("Usuario actualizado.", "success")
            return redirect(url_for("admin_usuarios"))
        users = get_db().execute("SELECT * FROM usuarios ORDER BY nombre").fetchall()
        return render_template("admin/usuarios.html", usuarios=users)

    @app.route("/documentos", methods=["GET", "POST"])
    @login_required
    def documentos():
        if request.method == "POST":
            if g.usuario["rol"] != "admin":
                abort(403)
            uploaded = request.files.get("archivo")
            filename = secure_filename(uploaded.filename or "") if uploaded else ""
            if not filename or Path(filename).suffix.lower() not in {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".docx", ".xlsx"}:
                flash("Selecciona un PDF, TXT, imagen, DOCX o XLSX (máximo 10 MB).", "error")
            else:
                try:
                    validate_document(uploaded, filename)
                except ValueError as exc:
                    flash(str(exc), 'error')
                    return redirect(url_for('documentos'))
                folder = Path(current_app.config["UPLOAD_FOLDER"])
                folder.mkdir(parents=True, exist_ok=True)
                storage_name = secrets.token_hex(24) + Path(filename).suffix.lower()
                uploaded.save(folder / storage_name)
                try:
                    cursor = get_db().execute("INSERT INTO documentos(nombre,archivo,autor_id) VALUES(?,?,?)",
                                     (filename, storage_name, g.usuario["id"]))
                    audit('crear','documento',cursor.lastrowid)
                    get_db().commit()
                except Exception:
                    (folder / storage_name).unlink(missing_ok=True)
                    raise
                flash("Documento guardado.", "success")
                return redirect(url_for("documentos"))
        docs = get_db().execute("SELECT * FROM documentos WHERE archivado=0 ORDER BY id DESC").fetchall()
        return render_template("documentos.html", documentos=docs)

    @app.get("/documentos/<int:record_id>")
    @login_required
    def descargar_documento(record_id):
        doc = record("documentos", record_id)
        if doc['archivado'] and g.usuario['rol'] != 'admin':
            abort(404)
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], doc["archivo"],
                                   as_attachment=True, download_name=doc["nombre"])

    @app.post("/documentos/<int:record_id>/eliminar")
    @admin_required
    def eliminar_documento(record_id):
        doc = record("documentos", record_id)
        get_db().execute("UPDATE documentos SET archivado=1 WHERE id=?", (record_id,))
        audit('archivar','documento',record_id)
        get_db().commit()
        flash("Documento archivado.", "success")
        return redirect(url_for("documentos"))
