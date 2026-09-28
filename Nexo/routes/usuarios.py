from flask import flash, g, redirect, render_template, request, url_for
from app import get_db
from app.organizacion import areas
from app.usuario import login_required

def register(app):
    @app.get("/personas")
    @login_required
    def personas():
        query = request.args.get("q", "").strip()
        area = request.args.get("area", "")
        people = get_db().execute(
            """SELECT id,nombre,apellidos,correo,area,puesto,disponibilidad FROM usuarios
            WHERE activo=1 AND verificado=1 AND (nombre||' '||apellidos||' '||correo LIKE ?)
            AND (?='' OR area=?) ORDER BY nombre""", ("%" + query + "%", area, area)).fetchall()
        return render_template("usuarios/directorio.html", personas=people, areas=areas())

    @app.route("/perfil", methods=["GET", "POST"])
    @login_required
    def perfil():
        if request.method == "POST":
            values = [request.form.get(key, "").strip() for key in ("nombre", "apellidos", "area", "puesto", "disponibilidad")]
            if not values[0] or any(len(value) > 200 for value in values) or values[-1] not in ("Disponible", "Ocupado", "Ausente"):
                flash("Revisa los campos del perfil.", "error")
            else:
                get_db().execute("UPDATE usuarios SET nombre=?,apellidos=?,area=?,puesto=?,disponibilidad=? WHERE id=?",
                                 (*values, g.usuario["id"]))
                get_db().commit()
                flash("Perfil actualizado.", "success")
                return redirect(url_for("perfil"))
        return render_template("usuarios/perfil.html")
