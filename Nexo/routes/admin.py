from datetime import date, datetime
from pathlib import Path
import secrets
from flask import abort, flash, g, redirect, render_template, request, send_from_directory, url_for, current_app
from werkzeug.utils import secure_filename
from app import get_db
from app.convocatoria import list_calls
from app.usuario import admin_required, login_required

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
    @app.get("/admin")
    @admin_required
    def admin():
        db = get_db()
        calls = list_calls()
        stats = {
            "usuarios": db.execute("SELECT count(*) FROM usuarios").fetchone()[0],
            "publicaciones": db.execute("SELECT count(*) FROM publicaciones").fetchone()[0],
            "convocatorias": sum(item["estado"] == "Vigente" for item in calls),
            "mensajes": db.execute("SELECT count(*) FROM mensajes WHERE date(creado)=date('now')").fetchone()[0],
        }
        recent = db.execute("SELECT * FROM publicaciones ORDER BY id DESC LIMIT 5").fetchall()
        return render_template("admin/dashboard.html", stats=stats, publicaciones=recent, convocatorias=calls[:5])

    @app.route("/admin/publicaciones", methods=["GET", "POST"])
    @admin_required
    def admin_publicaciones():
        edit = request.args.get("editar", type=int)
        item = record("publicaciones", edit) if edit else None
        if request.method == "POST":
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
                values = (title, content, kind, status, start, end)
                if item:
                    get_db().execute("UPDATE publicaciones SET titulo=?,contenido=?,tipo=?,estado=?,fecha=?,vencimiento=? WHERE id=?",
                                     (*values, item["id"]))
                else:
                    get_db().execute("INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,vencimiento,autor_id) VALUES(?,?,?,?,?,?,?)",
                                     (*values, g.usuario["id"]))
                get_db().commit()
                flash("Publicación guardada.", "success")
                return redirect(url_for("admin_publicaciones"))
            except ValueError as exc:
                flash(str(exc), "error")
        items = get_db().execute("SELECT * FROM publicaciones ORDER BY id DESC").fetchall()
        return render_template("admin/publicaciones.html", publicaciones=items, item=item, hoy=date.today().isoformat())

    @app.post("/admin/publicaciones/<int:record_id>/eliminar")
    @admin_required
    def eliminar_publicacion(record_id):
        record("publicaciones", record_id)
        get_db().execute("DELETE FROM publicaciones WHERE id=?", (record_id,))
        get_db().commit()
        flash("Publicación eliminada.", "success")
        return redirect(url_for("admin_publicaciones"))

    @app.route("/admin/convocatorias", methods=["GET", "POST"])
    @admin_required
    def admin_convocatorias():
        edit = request.args.get("editar", type=int)
        item = record("convocatorias", edit) if edit else None
        if request.method == "POST":
            try:
                title, content, area, place = required("titulo"), required("contenido", 20000), required("area"), required("lugar")
                start = datetime.fromisoformat(required("inicio"))
                end = datetime.fromisoformat(required("fin"))
                if start.tzinfo or end.tzinfo:
                    raise ValueError("Usa fechas en la hora local de la institución.")
                if end < start:
                    raise ValueError("El cierre no puede ser anterior al inicio.")
                values = (title, content, area, place, start.isoformat(timespec="minutes"), end.isoformat(timespec="minutes"))
                if item:
                    get_db().execute("UPDATE convocatorias SET titulo=?,contenido=?,area=?,lugar=?,inicio=?,fin=? WHERE id=?",
                                     (*values, item["id"]))
                else:
                    get_db().execute("INSERT INTO convocatorias(titulo,contenido,area,lugar,inicio,fin,autor_id) VALUES(?,?,?,?,?,?,?)",
                                     (*values, g.usuario["id"]))
                get_db().commit()
                flash("Convocatoria guardada.", "success")
                return redirect(url_for("admin_convocatorias"))
            except ValueError as exc:
                flash(str(exc), "error")
        return render_template("admin/convocatorias.html", convocatorias=list_calls(), item=item)

    @app.post("/admin/convocatorias/<int:record_id>/eliminar")
    @admin_required
    def eliminar_convocatoria(record_id):
        record("convocatorias", record_id)
        get_db().execute("DELETE FROM convocatorias WHERE id=?", (record_id,))
        get_db().commit()
        flash("Convocatoria eliminada.", "success")
        return redirect(url_for("admin_convocatorias"))

    @app.route("/admin/usuarios", methods=["GET", "POST"])
    @admin_required
    def admin_usuarios():
        if request.method == "POST":
            user_id = request.form.get("usuario_id", type=int)
            record("usuarios", user_id)
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
                folder = Path(current_app.config["UPLOAD_FOLDER"])
                folder.mkdir(parents=True, exist_ok=True)
                storage_name = secrets.token_hex(24) + Path(filename).suffix.lower()
                uploaded.save(folder / storage_name)
                try:
                    get_db().execute("INSERT INTO documentos(nombre,archivo,autor_id) VALUES(?,?,?)",
                                     (filename, storage_name, g.usuario["id"]))
                    get_db().commit()
                except Exception:
                    (folder / storage_name).unlink(missing_ok=True)
                    raise
                flash("Documento guardado.", "success")
                return redirect(url_for("documentos"))
        docs = get_db().execute("SELECT * FROM documentos ORDER BY id DESC").fetchall()
        return render_template("documentos.html", documentos=docs)

    @app.get("/documentos/<int:record_id>")
    @login_required
    def descargar_documento(record_id):
        doc = record("documentos", record_id)
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], doc["archivo"],
                                   as_attachment=True, download_name=doc["nombre"])

    @app.post("/documentos/<int:record_id>/eliminar")
    @admin_required
    def eliminar_documento(record_id):
        doc = record("documentos", record_id)
        get_db().execute("DELETE FROM documentos WHERE id=?", (record_id,))
        get_db().commit()
        (Path(current_app.config["UPLOAD_FOLDER"]) / doc["archivo"]).unlink(missing_ok=True)
        flash("Documento eliminado.", "success")
        return redirect(url_for("documentos"))
