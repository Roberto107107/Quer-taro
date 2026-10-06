"""NEXO application factory, database lifecycle and request protection."""
import hmac
import os
import secrets
import sqlite3
from pathlib import Path
import click
from flask import Flask, abort, current_app, g, render_template, request, session
from werkzeug.exceptions import HTTPException, SecurityError
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
CREATE TABLE IF NOT EXISTS enterados_publicaciones (
 usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
 publicacion_id INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
 PRIMARY KEY (usuario_id, publicacion_id)
);
CREATE TABLE IF NOT EXISTS enterados_convocatorias (
 usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
 convocatoria_id INTEGER NOT NULL REFERENCES convocatorias(id) ON DELETE CASCADE,
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
 PRIMARY KEY (usuario_id, convocatoria_id)
);
CREATE TABLE IF NOT EXISTS enterados_documentos (
 usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
 documento_id INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
 PRIMARY KEY (usuario_id, documento_id)
);
CREATE TABLE IF NOT EXISTS postulaciones (
 usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
 convocatoria_id INTEGER NOT NULL REFERENCES convocatorias(id) ON DELETE CASCADE,
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
 PRIMARY KEY (usuario_id, convocatoria_id)
);
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
    if app.config['PRODUCTION']:
        if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
            raise RuntimeError('Producción requiere SECRET_KEY aleatoria de al menos 32 caracteres en el entorno.')
        if not app.config['TRUSTED_HOSTS']:
            raise RuntimeError('Producción requiere NEXO_TRUSTED_HOSTS con los dominios permitidos.')
        if app.debug or os.environ.get('FLASK_DEBUG') == '1':
            raise RuntimeError('La depuración no está permitida en producción.')
        app.config['SESSION_COOKIE_SECURE'] = True
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        key = Path(app.instance_path) / "secret.key"
        try:
            with os.fdopen(os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as stream:
                stream.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config["SECRET_KEY"] = key.read_text(encoding="utf-8").strip()
    if not app.config['SECRET_KEY']:
        raise RuntimeError('La clave de sesión no puede estar vacía.')
    if not app.config["DATABASE"]:
        app.config["DATABASE"] = str(Path(app.instance_path) / "nexo.sqlite3")
    if not app.config.get("UPLOAD_FOLDER"):
        app.config["UPLOAD_FOLDER"] = str(Path(app.instance_path) / "uploads")

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    with app.app_context():
        get_db().executescript(SCHEMA)
        for table in ('publicaciones', 'convocatorias'):
            columns = {row['name'] for row in get_db().execute(f'PRAGMA table_info({table})')}
            if 'imagen' not in columns:
                get_db().execute(f'ALTER TABLE {table} ADD COLUMN imagen TEXT')
        columns = {row['name'] for row in get_db().execute('PRAGMA table_info(postulaciones)')}
        for name, definition in {
            'estado': "TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente','aceptada','rechazada'))",
            'revisado_por': 'INTEGER REFERENCES usuarios(id)',
            'revisado': 'TEXT',
        }.items():
            if name not in columns:
                get_db().execute(f'ALTER TABLE postulaciones ADD COLUMN {name} {definition}')
        get_db().commit()
        from app.acuerdo import SCHEMA as AGREEMENTS_SCHEMA
        get_db().executescript(AGREEMENTS_SCHEMA)
        from app.security import SCHEMA as SECURITY_SCHEMA
        get_db().executescript(SECURITY_SCHEMA)
        from app.seguimiento import migrate
        migrate()

    from app.security import register_headers, valid_session, end_session, limit_auth_requests
    register_headers(app)

    @app.before_request
    def load_user_and_protect_forms():
        g.usuario = None
        if session.get("usuario_id"):
            g.usuario = get_db().execute(
                "SELECT * FROM usuarios WHERE id = ? AND activo = 1 AND verificado = 1",
                (session["usuario_id"],)).fetchone()
            if g.usuario is None or not valid_session(session['usuario_id']):
                end_session()
                g.usuario = None
        session.setdefault("csrf", secrets.token_hex(32))
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            token = request.form.get("csrf_token", "")
            if not hmac.compare_digest(token.encode('utf-8'), session["csrf"].encode('utf-8')):
                abort(400, "El formulario caducó. Recarga la página y vuelve a intentarlo.")
            if request.endpoint in ('login', 'registro'):
                limit_auth_requests()

    @app.context_processor
    def context():
        from app.notificacion import unread_count
        from app.acuerdo import pending_count
        user = g.get('usuario')
        return {"usuario": user, "csrf_token": session.get("csrf", ""),
                "avisos_pendientes": get_db().execute('SELECT count(*) FROM notificaciones WHERE usuario_id=? AND leida=0', (user['id'],)).fetchone()[0] if user else 0,
                "acuerdos_pendientes": pending_count(user['id']) if user else 0,
                "sin_leer": unread_count(user["id"]) if user else 0}

    @app.errorhandler(HTTPException)
    def http_error(error):
        if isinstance(error, SecurityError):
            return 'Solicitud no válida.', 400
        if error.code == 500:
            g.usuario = None
        return render_template("error.html", error=error), error.code

    from routes import register_routes
    register_routes(app)
    from routes.seguimiento import register as register_followup
    register_followup(app)
    from app.respaldo import register_commands
    register_commands(app)

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
        get_db().execute('DELETE FROM auth_sessions WHERE usuario_id IN (SELECT id FROM usuarios WHERE correo=?)', (correo,))
        get_db().commit()
        if cursor.rowcount == 0:
            raise click.ClickException("Usuario no encontrado.")
        click.echo("Contraseña actualizada.")

    return app
