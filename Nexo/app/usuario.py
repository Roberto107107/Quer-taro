"""User validation, authentication guards and verification tokens."""
from functools import wraps
import re
from flask import abort, current_app, g, redirect, url_for
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash
from app import get_db

def password_hash(password):
    if len(password) < 10 or len(password) > 256:
        raise ValueError("La contraseña debe tener entre 10 y 256 caracteres.")
    return generate_password_hash(password)

def create_user(nombre, apellidos, correo, password, area="", puesto="", rol="usuario", verificado=0):
    correo = correo.strip().lower()
    if not nombre.strip() or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", correo):
        raise ValueError("Escribe un nombre y un correo válidos.")
    if any(len(value) > 200 for value in (nombre, apellidos, correo, area, puesto)):
        raise ValueError("Los campos no deben exceder 200 caracteres.")
    cursor = get_db().execute(
        "INSERT INTO usuarios(nombre,apellidos,correo,password,area,puesto,rol,verificado) VALUES(?,?,?,?,?,?,?,?)",
        (nombre.strip(), apellidos.strip(), correo, password_hash(password), area.strip(), puesto.strip(), rol, verificado))
    get_db().commit()
    return cursor.lastrowid

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.usuario["rol"] != "admin":
            abort(403, "Esta sección requiere permisos de administración.")
        return view(*args, **kwargs)
    return wrapped

def verification_token(user):
    return URLSafeTimedSerializer(current_app.secret_key, salt="nexo-verificar").dumps(
        {"id": user["id"], "correo": user["correo"]})
