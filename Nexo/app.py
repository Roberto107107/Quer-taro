from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

app.secret_key = "clave-temporal-nexo"


# =========================
# DATOS TEMPORALES
# =========================

usuario_actual = {
    "nombre": "Roberto",
    "apellidos": "Usuario",
    "correo": "usuario@organizacion.gob.mx",
    "area": "Gobierno Digital",
    "puesto": "Desarrollador",
    "rol": "usuario"
}


# =========================
# RUTAS
# =========================

@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login")
def login():
    return render_template("auth/login.html")


@app.route("/registro")
def registro():
    return render_template("auth/registro.html")


@app.route("/inicio")
def inicio():
    return render_template(
        "main/inicio.html",
        usuario=usuario_actual
    )


@app.route("/mensajes")
def mensajes():
    return render_template(
        "chat/mensajes.html",
        usuario=usuario_actual
    )


@app.route("/personas")
def personas():
    return render_template(
        "usuarios/directorio.html",
        usuario=usuario_actual
    )


@app.route("/perfil")
def perfil():
    return render_template(
        "usuarios/perfil.html",
        usuario=usuario_actual
    )


@app.route("/convocatorias")
def convocatorias():
    return render_template(
        "convocatorias/index.html",
        usuario=usuario_actual
    )


##Rutas de administración
@app.route("/admin")
def admin():
    return render_template(
        "admin/dashboard.html",
        usuario=usuario_actual
    )

@app.route("/admin/publicaciones")
def admin_publicaciones():
    return render_template(
        "admin/publicaciones.html",
        usuario=usuario_actual
    )


if __name__ == "__main__":
    app.run(debug=True)