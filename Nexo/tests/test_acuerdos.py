from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from app import create_app, get_db
from app.usuario import create_user


class AgreementTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test',
                               'DATABASE': str(Path(self.temp.name) / 'test.sqlite')})
        self.client = self.app.test_client()
        with self.app.app_context():
            self.creator = create_user('Ana', '', 'ana@test.mx', 'password1234', verificado=1)
            self.owner = create_user('Luis', '', 'luis@test.mx', 'password1234', verificado=1)
            self.admin = create_user('Admin', '', 'admin@test.mx', 'password1234', verificado=1, rol='admin')
            db = get_db()
            self.message = db.execute('INSERT INTO mensajes(remitente_id,destinatario_id,contenido) VALUES(?,?,?)',
                                      (self.creator, self.owner, 'Contenido privado del mensaje')).lastrowid
            db.commit()
        self.signin(self.creator)

    def tearDown(self):
        self.temp.cleanup()

    def signin(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session['usuario_id'] = user_id
            session['csrf'] = 'test-token'

    def post(self, url, values=None):
        return self.client.post(url, data={'csrf_token': 'test-token', **(values or {})})

    def create(self, **changes):
        values = {'titulo': 'Acuerdo privado', 'descripcion': 'Descripcion privada',
                  'responsable_id': self.owner, 'fecha_limite': (date.today() + timedelta(days=2)).isoformat()}
        values.update(changes)
        return self.post(f'/mensajes/{self.message}/acuerdo', values)

    def test_full_lifecycle_and_audit(self):
        self.assertEqual(self.create().status_code, 302)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'pendiente'}).status_code, 403)
        self.signin(self.owner)
        self.assertIn(b'nav-counter', self.client.get('/acuerdos').data)
        for state in ('pendiente', 'en_proceso'):
            self.assertEqual(self.post('/acuerdos/1', {'estado': state}).status_code, 302)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'completado'}).status_code, 200)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'completado', 'nota': 'Resultado entregado'}).status_code, 302)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'pendiente'}).status_code, 403)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT estado FROM acuerdos').fetchone()[0], 'completado')
            self.assertEqual(get_db().execute('SELECT count(*) FROM acuerdo_historial').fetchone()[0], 4)
        detail = self.client.get('/acuerdos/1')
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b'Resultado entregado', detail.data)

    def test_privacy_including_nonparticipant_admin(self):
        self.create()
        self.signin(self.admin)
        self.assertEqual(self.client.get('/acuerdos/1').status_code, 404)
        self.assertEqual(self.post('/acuerdos/1', {'estado':'cancelado', 'nota':'x'}).status_code, 404)
        self.assertEqual(self.client.get(f'/mensajes/{self.message}/acuerdo').status_code, 404)
        self.assertEqual(self.create().status_code, 404)
        for url in ('/admin/acuerdos', '/acuerdos'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            for private in (b'Contenido privado', b'Acuerdo privado', b'Descripcion privada', b'Luis'):
                self.assertNotIn(private, response.data)
        self.signin(self.owner)
        self.assertEqual(self.client.get('/admin/acuerdos').status_code, 403)

    def test_creation_validation_and_csrf(self):
        self.assertEqual(self.create(responsable_id=self.admin).status_code, 200)
        self.assertEqual(self.create(fecha_limite='invalid').status_code, 200)
        self.assertEqual(self.create(fecha_limite='2020-01-01').status_code, 200)
        self.assertEqual(self.create(titulo='').status_code, 200)
        self.assertEqual(self.client.post(f'/mensajes/{self.message}/acuerdo', data={}).status_code, 400)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM acuerdos').fetchone()[0], 0)

    def test_reject_cancel_and_invalid_transitions(self):
        self.create()
        self.signin(self.owner)
        self.assertEqual(self.post('/acuerdos/1', {'estado':'completado','nota':'x'}).status_code, 403)
        self.assertEqual(self.post('/acuerdos/1', {'estado':'cancelado','nota':'x'}).status_code, 403)
        self.assertEqual(self.post('/acuerdos/1', {'estado':'rechazado','nota':'No corresponde'}).status_code, 302)
        self.signin(self.creator)
        self.assertEqual(self.post('/acuerdos/1', {'estado':'cancelado','nota':'x'}).status_code, 403)
        self.create()
        self.assertEqual(self.post('/acuerdos/2', {'estado':'cancelado','nota':'Ya no se requiere'}).status_code, 302)

    def test_overdue_filter_escaping_and_chat_entry_point(self):
        self.create(titulo='<script>alert(1)</script>')
        with self.app.app_context():
            get_db().execute("UPDATE acuerdos SET fecha_limite='2020-01-01'")
            get_db().commit()
        response = self.client.get('/acuerdos?estado=vencidos')
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert(1)</script>', response.data)
        self.assertIn(b'deadline-late', response.data)
        self.assertNotIn(b'alert(1)', self.client.get('/acuerdos?estado=completado').data)
        self.assertNotIn(b'alert(1)', self.client.get('/acuerdos?estado=activos').data)
        self.signin(self.owner)
        self.post('/acuerdos/1', {'estado': 'pendiente'})
        self.assertIn(b'alert(1)', self.client.get('/acuerdos?estado=activos').data)
        self.signin(self.creator)
        self.assertIn(f'/mensajes/{self.message}/acuerdo'.encode(), self.client.get(f'/mensajes?usuario={self.owner}').data)
        self.assertEqual(self.client.get(f'/mensajes/{self.message}/acuerdo').status_code, 200)

    def test_schema_reinitialization_preserves_agreements(self):
        self.create()
        second = create_app(dict(self.app.config))
        with second.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM acuerdos').fetchone()[0], 1)
            self.assertEqual(get_db().execute('SELECT count(*) FROM mensajes').fetchone()[0], 1)
