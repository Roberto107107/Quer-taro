import io
import secrets
import tempfile
import unittest
import threading
from urllib.request import urlopen
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from app import create_app, get_db
from app.usuario import create_user
from app.security import token_hash


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.secret = secrets.token_hex(32)
        self.password = secrets.token_urlsafe(24)
        self.app = create_app({'TESTING': True, 'SECRET_KEY': self.secret,
            'DATABASE': str(Path(self.tmp.name) / 'security.sqlite'),
            'UPLOAD_FOLDER': str(Path(self.tmp.name) / 'uploads')})
        self.client = self.app.test_client()
        with self.app.app_context():
            self.uid = create_user('Security', '', 'audit@example.test', self.password, verificado=1)

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, data=None):
        self.client.get('/login')
        with self.client.session_transaction() as s:
            csrf = s['csrf']
        return self.client.post(path, data={'csrf_token': csrf, **(data or {})})

    def login(self):
        return self.post('/login', {'correo': 'audit@example.test', 'password': self.password})

    def test_headers_success_redirect_errors_and_static(self):
        for path in ('/login', '/inicio', '/missing', '/static/js/main.js'):
            response = self.client.get(path)
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
            self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
            csp = response.headers['Content-Security-Policy']
            self.assertIn("frame-ancestors 'none'", csp)
            self.assertNotIn('unsafe-inline', csp)
            self.assertNotIn('unsafe-eval', csp)
            self.assertNotIn('Server', response.headers)
            if not path.startswith('/static'):
                self.assertIn('no-store', response.headers['Cache-Control'])
            response.close()

    def test_local_http_server_does_not_add_server_header(self):
        from werkzeug.serving import make_server
        from app.security import LocalRequestHandler
        server = make_server('127.0.0.1', 0, self.app, request_handler=LocalRequestHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with urlopen(f'http://127.0.0.1:{server.server_port}/login', timeout=5) as response:
                self.assertNotIn('Server', response.headers)
                self.assertIn('Content-Security-Policy', response.headers)
        finally:
            server.shutdown()
            worker.join(timeout=5)
            server.server_close()

    def test_waitress_http_server_does_not_add_server_header(self):
        try:
            from waitress import create_server
        except ImportError:
            self.skipTest('Install requirements-production.txt for WSGI transport verification.')
        server = create_server(self.app, host='127.0.0.1', port=0, ident='', map={})
        worker = threading.Thread(target=server.run, daemon=True)
        worker.start()
        try:
            with urlopen(f'http://127.0.0.1:{server.effective_port}/login', timeout=5) as response:
                self.assertNotIn('Server', response.headers)
                self.assertIn('Content-Security-Policy', response.headers)
        finally:
            server.task_dispatcher.shutdown()
            server.close()
            worker.join(timeout=5)

    def test_reflected_attributes_do_not_create_html_or_events(self):
        payload = '\"><img src=x onerror=alert(1)><input autofocus onfocus=alert(1) value="'
        for path, values, field in [('/login', {'correo': payload, 'password': self.password}, 'correo'),
                ('/registro', {'nombre': payload, 'correo': 'invalid', 'password': self.password,
                               'confirmacion': self.password}, 'nombre')]:
            response = self.post(path, values)
            parsed = Tags(response.get_data(as_text=True))
            inputs = [attrs for tag, attrs in parsed.tags if tag == 'input' and attrs.get('name') == field]
            self.assertEqual(inputs[0]['value'], payload)
            self.assertFalse(any(key.startswith('on') for _, attrs in parsed.tags for key in attrs))
            self.assertFalse(any(tag == 'img' and attrs.get('src') == 'x' for tag, attrs in parsed.tags))
            self.assertNotIn(self.password, response.get_data(as_text=True))

    def test_csrf_unicode_missing_and_sql_payload(self):
        self.client.get('/login')
        for token in ('', 'incorrect', '\u2603'):
            self.assertEqual(self.client.post('/login', data={'csrf_token': token}).status_code, 400)
        self.assertEqual(self.post('/login', {'correo': "' OR 1=1 --", 'password': self.password}).status_code, 200)
        self.assertEqual(self.client.get('/perfil').status_code, 302)

    def test_session_rotation_logout_replay_expiry_and_reset(self):
        self.client.get('/login')
        with self.client.session_transaction() as s:
            old_csrf = s['csrf']
        self.login()
        with self.client.session_transaction() as s:
            self.assertNotEqual(s['csrf'], old_csrf)
            self.assertTrue(s.permanent)
        cookie = self.client.get_cookie('session').value
        self.post('/logout')
        self.client.set_cookie('session', cookie)
        self.assertEqual(self.client.get('/perfil').status_code, 302)
        self.login()
        with self.client.session_transaction() as s:
            token = s['auth_token']
        with self.app.app_context():
            get_db().execute('UPDATE auth_sessions SET expires=0 WHERE token_hash=?', (token_hash(token),))
            get_db().commit()
        self.assertEqual(self.client.get('/perfil').status_code, 302)
        self.login()
        new_password = secrets.token_urlsafe(24)
        result = self.app.test_cli_runner().invoke(args=['reset-password', 'audit@example.test'],
                                                  input=new_password + '\n' + new_password + '\n')
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(self.client.get('/perfil').status_code, 302)

    def test_production_guards_cookie_and_untrusted_host(self):
        settings = dict(self.app.config)
        settings.update(PRODUCTION=True, TRUSTED_HOSTS=['localhost'], DEBUG=False)
        with self.assertRaises(RuntimeError):
            create_app({**settings, 'SECRET_KEY': ''})
        with self.assertRaises(RuntimeError):
            create_app({**settings, 'TRUSTED_HOSTS': None})
        production = create_app(settings).test_client()
        response = production.get('/login', base_url='https://localhost')
        cookie = response.headers['Set-Cookie']
        for flag in ('Secure', 'HttpOnly', 'SameSite=Lax'):
            self.assertIn(flag, cookie)
        self.assertIn('Strict-Transport-Security', response.headers)
        self.assertEqual(production.get('/login', base_url='https://untrusted.test').status_code, 400)

    def test_rate_limit_survives_client_cookie_change(self):
        self.app.config['AUTH_RATE_LIMIT'] = 2
        for _ in range(2):
            self.assertEqual(self.post('/login', {'correo': 'invalid'}).status_code, 200)
        self.client = self.app.test_client()
        response = self.post('/login', {'correo': 'invalid'})
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response.headers)

    def test_document_disguise_is_rejected(self):
        self.login()
        with self.app.app_context():
            get_db().execute("UPDATE usuarios SET rol='admin' WHERE id=?", (self.uid,))
            get_db().commit()
        for name in ('fake.pdf', 'fake.png', 'fake.docx', 'fake.xlsx'):
            response = self.post('/documentos', {'archivo': (io.BytesIO(b'<script>alert(1)</script>'), name)})
            self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM documentos').fetchone()[0], 0)

    def test_internal_error_does_not_expose_exception(self):
        self.app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
        with patch('routes.auth.get_db', side_effect=RuntimeError('sensitive internal detail')):
            with self.assertLogs(self.app.logger, level='ERROR'):
                result = self.post('/login', {'correo': 'audit@example.test'})
        self.assertEqual(result.status_code, 500)
        self.assertNotIn(b'sensitive internal detail', result.data)
        self.assertEqual(result.headers['X-Content-Type-Options'], 'nosniff')
