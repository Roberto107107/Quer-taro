"""NEXO application factory, database lifecycle and request protection."""
import hmac
import os
import secrets
import sqlite3
from pathlib import Path
import click
from flask import Flask, abort, current_app, g, render_template, request, session
from werkzeug.exceptions import HTTPException
from config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
 id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, apellidos TEXT NOT NULL,
 correo TEXT UNIQUE NOT NULL COLLATE NOCASE, password TEXT NOT NULL,
 area TEXT NOT NULL DEFAULT '', puesto TEXT NOT NULL DEFAULT '',
 rol TEXT NOT NULL DEFAULT 'usuario' CHECK(rol IN ('usuario','admin')),
 activo INTEGER NOT NULL DEFAULT 1, verificado INTEGER NOT NULL DEFAULT 0,
 disponibilidad TEXT NOT NULL DEFAULT 'Disponible',
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE TABLE IF NOT EXISTS publicaciones (
 id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, contenido TEXT NOT NULL,
 tipo TEXT NOT NULL, estado TEXT NOT NULL, fecha TEXT NOT NULL,
 vencimiento TEXT, autor_id INTEGER NOT NULL REFERENCES usuarios(id),
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE TABLE IF NOT EXISTS convocatorias (
 id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, contenido TEXT NOT NULL,
 area TEXT NOT NULL, lugar TEXT NOT NULL, inicio TEXT NOT NULL,
 fin TEXT NOT NULL, autor_id INTEGER NOT NULL REFERENCES usuarios(id),
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE TABLE IF NOT EXISTS mensajes (
 id INTEGER PRIMARY KEY, remitente_id INTEGER NOT NULL REFERENCES usuarios(id),
 destinatario_id INTEGER NOT NULL REFERENCES usuarios(id), contenido TEXT NOT NULL,
 leido INTEGER NOT NULL DEFAULT 0,
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE TABLE IF NOT EXISTS documentos (
 id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, archivo TEXT NOT NULL UNIQUE,
 autor_id INTEGER NOT NULL REFERENCES usuarios(id),
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE INDEX IF NOT EXISTS mensajes_participantes ON mensajes(remitente_id, destinatario_id, id);
"""

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def create_app(test_config=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static",
                instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        key = Path(app.instance_path) / "secret.key"
        try:
            with key.open("x", encoding="utf-8") as stream:
                stream.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config["SECRET_KEY"] = key.read_text(encoding="utf-8").strip()
    if not app.config["DATABASE"]:
        app.config["DATABASE"] = str(Path(app.instance_path) / "nexo.sqlite3")
    app.config.setdefault("UPLOAD_FOLDER", str(Path(app.instance_path) / "uploads"))

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    with app.app_context():
        get_db().executescript(SCHEMA)
        from app.acuerdo import SCHEMA as AGREEMENTS_SCHEMA
        get_db().executescript(AGREEMENTS_SCHEMA)

    @app.before_request
    def load_user_and_protect_forms():
        g.usuario = None
        if session.get("usuario_id"):
            g.usuario = get_db().execute(
                "SELECT * FROM usuarios WHERE id = ? AND activo = 1 AND verificado = 1",
                (session["usuario_id"],)).fetchone()
            if g.usuario is None:
                session.clear()
        session.setdefault("csrf", secrets.token_hex(32))
        if request.method == "POST":
            token = request.form.get("csrf_token", "")
            if not hmac.compare_digest(token, session["csrf"]):
                abort(400, "El formulario caducó. Recarga la página y vuelve a intentarlo.")

    @app.context_processor
    def context():
        from app.notificacion import unread_count
        from app.acuerdo import pending_count
        return {"usuario": g.usuario, "csrf_token": session.get("csrf", ""),
                "acuerdos_pendientes": pending_count(g.usuario['id']) if g.usuario else 0,
                "sin_leer": unread_count(g.usuario["id"]) if g.usuario else 0}

    @app.errorhandler(HTTPException)
    def http_error(error):
        return render_template("error.html", error=error), error.code

    from routes import register_routes
    register_routes(app)

    @app.cli.command("create-admin")
    @click.option("--correo", prompt=True)
    @click.option("--nombre", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(correo, nombre, password):
        """Create an administrator without hardcoded credentials."""
        from app.usuario import create_user
        try:
            create_user(nombre, "", correo, password, rol="admin", verificado=1)
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise click.ClickException(str(exc))
        click.echo("Administrador creado.")

    @app.cli.command("verification-link")
    @click.argument("correo")
    @click.option("--base-url", default="http://127.0.0.1:5000")
    def verification_link(correo, base_url):
        """Generate a link for an operator to deliver after checking identity."""
        from app.usuario import verification_token
        user = get_db().execute("SELECT * FROM usuarios WHERE correo = ?", (correo,)).fetchone()
        if user is None:
            raise click.ClickException("Usuario no encontrado.")
        click.echo(base_url.rstrip("/") + "/verificar/" + verification_token(user))

    @app.cli.command("reset-password")
    @click.argument("correo")
    @click.password_option(confirmation_prompt=True)
    def reset_password(correo, password):
        from app.usuario import password_hash
        try:
            hashed = password_hash(password)
        except ValueError as exc:
            raise click.ClickException(str(exc))
        cursor = get_db().execute("UPDATE usuarios SET password = ? WHERE correo = ?", (hashed, correo))
        get_db().commit()
        if cursor.rowcount == 0:
            raise click.ClickException("Usuario no encontrado.")
        click.echo("Contraseña actualizada.")

    return app
