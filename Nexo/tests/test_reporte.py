from datetime import date
from io import BytesIO
from pathlib import Path
import secrets
import tempfile
import unittest
from pypdf import PdfReader
from app import create_app, get_db
from app.usuario import create_user
from app.reporte import report_period


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING': True, 'SECRET_KEY': secrets.token_hex(32),
                               'DATABASE': str(Path(self.temp.name) / 'reports.sqlite')})
        self.client = self.app.test_client()
        with self.app.app_context():
            self.creator = create_user('Ana', 'Pérez', 'creator@example.test', secrets.token_urlsafe(24), verificado=1)
            self.owner = create_user('José', 'Muñoz', 'owner@example.test', secrets.token_urlsafe(24), verificado=1)
            self.admin = create_user('Admin', '', 'admin@example.test', secrets.token_urlsafe(24), verificado=1, rol='admin')
            self.message = get_db().execute('INSERT INTO mensajes(remitente_id,destinatario_id,contenido) VALUES(?,?,?)',
                (self.creator, self.owner, 'Mensaje privado que no pertenece al reporte')).lastrowid
            get_db().commit()
        self.signin(self.creator)

    def tearDown(self):
        self.temp.cleanup()

    def signin(self, user_id):
        from flask import session
        from app.security import start_session
        with self.app.test_request_context():
            start_session(user_id)
            values = dict(session)
        with self.client.session_transaction() as client_session:
            client_session.clear()
            client_session.update(values)

    def add(self, title, completed, creator=None, owner=None, state='completado', description='Descripción del compromiso'):
        with self.app.app_context():
            db = get_db()
            aid = db.execute('''INSERT INTO acuerdos(mensaje_id,creador_id,responsable_id,titulo,descripcion,fecha_limite,estado)
                VALUES(?,?,?,?,?,'2030-01-01',?)''',
                (self.message, creator or self.creator, owner or self.owner, title, description, state)).lastrowid
            if completed:
                db.execute('INSERT INTO acuerdo_historial(acuerdo_id,actor_id,estado,nota,creado) VALUES(?,?,?,?,?)',
                           (aid, owner or self.owner, state, 'Resultado entregado', completed))
            db.commit()
            return aid

    def pdf(self, query):
        response = self.client.get('/acuerdos/reporte.pdf?' + query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))
        self.assertIn('attachment;', response.headers['Content-Disposition'])
        self.assertIn('no-store', response.headers['Cache-Control'])
        reader = PdfReader(BytesIO(response.data))
        response.close()
        return reader, '\n'.join(page.extract_text() for page in reader.pages)

    def test_period_boundaries(self):
        self.assertEqual(report_period('semana', '2026-01-01'), (date(2025, 12, 29), date(2026, 1, 5)))
        self.assertEqual(report_period('mes', '2024-02-29'), (date(2024, 2, 1), date(2024, 3, 1)))
        self.assertEqual(report_period('mes', '2026-12-31'), (date(2026, 12, 1), date(2027, 1, 1)))

    def test_week_includes_completion_not_deadline_or_feedback(self):
        self.add('Antes del periodo', '2026-10-04T23:59:59')
        aid = self.add('Inicio de semana', '2026-10-05T00:00:00')
        self.add('Fin de semana', '2026-10-11T23:59:59')
        self.add('Siguiente semana', '2026-10-12T00:00:00')
        self.add('Todavía en proceso', '2026-10-06T12:00:00', state='en_proceso')
        self.add('Sin fecha verificable', None)
        with self.app.app_context():
            get_db().execute("INSERT INTO acuerdo_historial(acuerdo_id,actor_id,estado,nota,creado) VALUES(?,?,'retroalimentacion','Comentario','2026-11-01T10:00:00')", (aid, self.creator))
            get_db().commit()
        _, text = self.pdf('periodo=semana&fecha=2026-10-07')
        self.assertIn('Total completados: 2', text)
        self.assertIn('Inicio de semana', text)
        self.assertIn('Fin de semana', text)
        self.assertIn('José Muñoz', text)
        for excluded in ('Antes del periodo', 'Siguiente semana', 'Todavía en proceso', 'Sin fecha verificable', 'Mensaje privado'):
            self.assertNotIn(excluded, text)

    def test_month_and_privacy_even_for_administrator(self):
        self.add('Primer día', '2026-10-01T00:00:00')
        self.add('Último día', '2026-10-31T23:59:59')
        self.add('Mes siguiente', '2026-11-01T00:00:00')
        self.add('Acuerdo ajeno', '2026-10-15T12:00:00', creator=self.admin, owner=self.admin)
        _, text = self.pdf('periodo=mes&fecha=2026-10-06&usuario_id=' + str(self.admin))
        self.assertIn('Total completados: 2', text)
        self.assertNotIn('Mes siguiente', text)
        self.assertNotIn('Acuerdo ajeno', text)
        self.signin(self.owner)
        self.assertIn('Primer día', self.pdf('periodo=mes&fecha=2026-10-06')[1])
        self.signin(self.admin)
        _, text = self.pdf('periodo=mes&fecha=2026-10-06')
        self.assertIn('Acuerdo ajeno', text)
        self.assertNotIn('Primer día', text)
        self.assertNotIn('Último día', text)

    def test_empty_invalid_and_anonymous(self):
        _, text = self.pdf('periodo=mes&fecha=2026-10-06')
        self.assertIn('No hay acuerdos completados', text)
        for query in ('periodo=otro', 'fecha=invalid', 'fecha=9999-12-31', 'fecha=2026-02-30'):
            self.assertEqual(self.client.get('/acuerdos/reporte.pdf?' + query).status_code, 400)
        self.assertEqual(self.app.test_client().get('/acuerdos/reporte.pdf').status_code, 302)
        self.assertIn(b'Descargar PDF', self.client.get('/acuerdos').data)

    def test_long_text_and_markup_are_safe_in_multipage_pdf(self):
        title = '<a href="https://example.test">Título & revisión</a>'
        description = ('Compromiso extenso con acentos y detalles. ' * 115)
        for n in range(6):
            self.add(title + str(n), '2026-10-06T12:00:00', description=description)
        reader, text = self.pdf('periodo=mes&fecha=2026-10-06')
        self.assertGreater(len(reader.pages), 1)
        self.assertIn(title, text)
        self.assertIn('Resultado entregado', text)
        self.assertFalse(any(page.get('/Annots') for page in reader.pages))
        self.assertIn('Total completados: 6', text)
