from flask import abort, flash, g, redirect, render_template, request, url_for
from app import get_db
from app.chat import conversation
from app.usuario import login_required

def register(app):
    @app.route("/mensajes", methods=["GET", "POST"])
    @login_required
    def mensajes():
        people = get_db().execute(
            "SELECT id,nombre,apellidos FROM usuarios WHERE activo=1 AND verificado=1 AND id<>? ORDER BY nombre",
            (g.usuario["id"],)).fetchall()
        other_id = request.args.get("usuario", type=int)
        other = next((row for row in people if row["id"] == other_id), None)
        if other_id is not None and other is None:
            abort(404, "Destinatario no disponible.")
        if request.method == "POST":
            content = request.form.get("contenido", "").strip()
            if other is None:
                abort(400, "Selecciona un destinatario.")
            if not content or len(content) > 5000:
                flash("Escribe un mensaje de entre 1 y 5000 caracteres.", "error")
            else:
                get_db().execute("INSERT INTO mensajes(remitente_id,destinatario_id,contenido) VALUES(?,?,?)",
                                 (g.usuario["id"], other["id"], content))
                get_db().commit()
                return redirect(url_for("mensajes", usuario=other["id"]))
        messages = conversation(g.usuario["id"], other["id"]) if other else []
        return render_template("chat/mensajes.html", personas=people, destinatario=other, mensajes=messages)

    @app.post("/mensajes/<int:other_id>/leidos")
    @login_required
    def mensajes_leidos(other_id):
        get_db().execute("UPDATE mensajes SET leido=1 WHERE remitente_id=? AND destinatario_id=?",
                         (other_id, g.usuario["id"]))
        get_db().commit()
        return redirect(url_for("mensajes", usuario=other_id))
