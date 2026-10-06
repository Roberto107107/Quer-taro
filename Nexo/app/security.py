"""HTTP defenses and revocable authentication without changing application routes."""
import hashlib
import hmac
import secrets
import time
from flask import abort, current_app, request, session
from app import get_db
from werkzeug.serving import WSGIRequestHandler

SCHEMA = """
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash TEXT PRIMARY KEY,
 usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 expires INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS auth_sessions_user ON auth_sessions(usuario_id);
CREATE TABLE IF NOT EXISTS auth_limits (
 bucket TEXT PRIMARY KEY, started INTEGER NOT NULL, attempts INTEGER NOT NULL
);
"""

CSP = (
    "default-src 'none'; script-src 'self'; script-src-attr 'none'; "
    "style-src 'self'; style-src-attr 'none'; img-src 'self' data: blob:; "
    "font-src 'self'; connect-src 'self'; form-action 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
)

def token_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def start_session(user_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    db = get_db()
    with db:
        db.execute('DELETE FROM auth_sessions WHERE expires<=?', (now,))
        db.execute('INSERT INTO auth_sessions(token_hash,usuario_id,expires) VALUES(?,?,?)',
                   (token_hash(token), user_id, now + int(current_app.permanent_session_lifetime.total_seconds())))
    session.clear()
    session.permanent = True
    session['usuario_id'] = user_id
    session['auth_token'] = token
    session['csrf'] = secrets.token_hex(32)

def valid_session(user_id):
    token = session.get('auth_token')
    return isinstance(token, str) and get_db().execute(
        'SELECT 1 FROM auth_sessions WHERE token_hash=? AND usuario_id=? AND expires>?',
        (token_hash(token), user_id, int(time.time()))).fetchone() is not None

def end_session():
    token = session.get('auth_token')
    if isinstance(token, str):
        get_db().execute('DELETE FROM auth_sessions WHERE token_hash=?', (token_hash(token),))
        get_db().commit()
    session.clear()

def limit_auth_requests():
    """Bound hashing/registration work across workers; do not trust forwarded IPs."""
    now = int(time.time())
    window = current_app.config['AUTH_RATE_WINDOW']
    identity = f'{request.endpoint}:{request.remote_addr or "unknown"}'
    bucket = hmac.new(current_app.secret_key.encode(), identity.encode(), hashlib.sha256).hexdigest()
    db = get_db()
    with db:
        db.execute('DELETE FROM auth_limits WHERE started<=?', (now - window,))
        db.execute('''INSERT INTO auth_limits(bucket,started,attempts) VALUES(?,?,1)
            ON CONFLICT(bucket) DO UPDATE SET attempts=attempts+1''', (bucket, now))
        row = db.execute('SELECT attempts,started FROM auth_limits WHERE bucket=?', (bucket,)).fetchone()
    if row['attempts'] > current_app.config['AUTH_RATE_LIMIT']:
        abort(429, 'Demasiados intentos. Espera unos minutos antes de volver a intentarlo.')

def register_headers(app):
    @app.after_request
    def security_headers(response):
        response.headers['Content-Security-Policy'] = CSP
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers.pop('Server', None)
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'private, no-store'
        if app.config['PRODUCTION']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        if response.status_code == 429:
            response.headers['Retry-After'] = str(app.config['AUTH_RATE_WINDOW'])
        return response

class LocalRequestHandler(WSGIRequestHandler):
    """Werkzeug adds Server after Flask hooks; suppress it at the actual emitter."""
    def send_header(self, keyword, value):
        if keyword.lower() != 'server':
            super().send_header(keyword, value)
