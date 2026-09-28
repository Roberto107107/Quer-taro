import secrets
import sqlite3
from flask import flash, g, redirect, render_template, request, session, url_for, current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash
from app import get_db
from app.usuario import create_user, login_required

def register(app):
    @app.route("/")
    def index():
        return redirect(url_for("inicio" if g.usuario else "login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.usuario:
            return redirect(url_for("inicio"))
        if request.method == "POST":
            user = get_db().execute("SELECT * FROM usuarios WHERE correo=?",
                                   (request.form.get("correo", "").strip().lower(),)).fetchone()
            if user and user["activo"] and check_password_hash(user["password"], request.form.get("password", "")):
                if not user["verificado"]:
                    flash("Tu cuenta está pendiente de verificación. Contacta a administración.", "error")
                else:
                    session.clear()
                    session["usuario_id"] = user["id"]
                    session["csrf"] = secrets.token_hex(32)
                    return redirect(url_for("inicio"))
            else:
                flash("Correo o contraseña incorrectos, o cuenta desactivada.", "error")
        return render_template("auth/login.html")

    @app.route("/registro", methods=["GET", "POST"])
    def registro():
        if request.method == "POST":
            try:
                if request.form.get("password") != request.form.get("confirmacion"):
                    raise ValueError("Las contraseñas no coinciden.")
                create_user(*(request.form.get(key, "") for key in
                              ("nombre", "apellidos", "correo", "password", "area", "puesto")))
            except ValueError as exc:
                flash(str(exc), "error")
            except sqlite3.IntegrityError:
                flash("Ese correo ya está registrado.", "error")
            else:
                flash("Cuenta creada. Administración debe verificarla antes del primer acceso.", "success")
                return redirect(url_for("login"))
        return render_template("auth/registro.html")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/verificar/<token>", methods=["GET", "POST"])
    def verificar(token):
        try:
            data = URLSafeTimedSerializer(current_app.secret_key, salt="nexo-verificar").loads(token, max_age=86400)
            user = get_db().execute("SELECT * FROM usuarios WHERE id=? AND correo=?",
                                   (data["id"], data["correo"])).fetchone()
            if user is None:
                raise BadSignature("Cuenta inexistente")
        except (BadSignature, SignatureExpired, KeyError):
            return render_template("auth/verificar.html", valido=False), 400
        if request.method == "POST":
            get_db().execute("UPDATE usuarios SET verificado=1 WHERE id=?", (user["id"],))
            get_db().commit()
            flash("Cuenta verificada. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("login"))
        return render_template("auth/verificar.html", valido=True)
