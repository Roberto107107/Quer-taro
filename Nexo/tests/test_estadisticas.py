from datetime import date
from io import BytesIO
from pathlib import Path
import secrets
import tempfile
import unittest
from pypdf import PdfReader
from app import create_app, get_db
from app.usuario import create_user
from app.estadisticas import dashboard_period, statistics


class AdminStatisticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING': True, 'SECRET_KEY': secrets.token_hex(32), 'DATABASE': str(Path(self.tmp.name)/'test.sqlite')})
        self.client = self.app.test_client()
        with self.app.app_context():
            self.admin = create_user('Admin', '', 'admin@example.test', secrets.token_urlsafe(24), rol='admin', verificado=1)
            self.user = create_user('PrivatePerson', '', 'user@example.test', secrets.token_urlsafe(24), verificado=1)
            db = get_db()
            db.execute("UPDATE usuarios SET creado='2026-01-01T00:00:00'")
            self.message = db.execute("INSERT INTO mensajes(remitente_id,destinatario_id,contenido,creado) VALUES(?,?,'SECRET MESSAGE','2026-10-01T00:00:00')", (self.user,self.user)).lastrowid
            db.execute("INSERT INTO mensajes(remitente_id,destinatario_id,contenido,creado) VALUES(?,?,'SECRET NEXT','2026-11-01T00:00:00')", (self.user,self.user))
            self.aid = db.execute("INSERT INTO acuerdos(mensaje_id,creador_id,responsable_id,titulo,descripcion,fecha_limite,estado) VALUES(?,?,?,'SECRET AGREEMENT','SECRET DESCRIPTION','2026-01-01','completado')", (self.message,self.user,self.user)).lastrowid
            db.execute("INSERT INTO acuerdo_historial(acuerdo_id,actor_id,estado,nota,creado) VALUES(?,?,'completado','SECRET NOTE','2026-10-31T23:59:59')", (self.aid,self.user))
            db.execute("INSERT INTO acuerdo_historial(acuerdo_id,actor_id,estado,nota,creado) VALUES(?,?,'retroalimentacion','SECRET FEEDBACK','2026-11-03T12:00:00')", (self.aid,self.user))
            db.execute("INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,autor_id,creado) VALUES('Post','Body','Aviso','draft','2026-01-01',?,'2026-10-05T00:00:00')", (self.admin,))
            db.commit()
        self.signin(self.admin)

    def tearDown(self):
        self.tmp.cleanup()

    def signin(self, uid):
        from flask import session
        from app.security import start_session
        with self.app.test_request_context():
            start_session(uid)
            auth = dict(session)
        with self.client.session_transaction() as target:
            target.clear()
            target.update(auth)

    def test_dates_and_aggregates(self):
        self.assertEqual(dashboard_period('anio','2024-02-29'), (date(2024,1,1),date(2025,1,1)))
        with self.app.app_context():
            data = statistics('mes', *dashboard_period('mes','2026-10-06'))
            values = {row['label']:row['value'] for row in data['metrics']}
            self.assertEqual(values['Mensajes enviados'],1)
            self.assertEqual(values['Acuerdos completados'],1)
            self.assertEqual(values['Publicaciones creadas'],1)
            self.assertEqual(values['Usuarios registrados'],0)
            self.assertEqual(len(data['timeline']),31)
            self.assertEqual(data['timeline'][-1]['value'],1)
            annual = statistics('anio', *dashboard_period('anio','2026-10-06'))
            self.assertEqual(len(annual['timeline']),12)
            self.assertEqual(annual['timeline'][9]['value'],1)
            self.assertEqual(sum(row['value'] for row in annual['timeline']),1)

    def test_pdf_and_dashboard_privacy(self):
        page = self.client.get('/admin?periodo=mes&fecha=2026-10-06')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'<svg',page.data)
        for period in ('semana','mes','anio'):
            response = self.client.get(f'/admin/reporte.pdf?periodo={period}&fecha=2026-10-06')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.mimetype,'application/pdf')
            self.assertIn('no-store',response.headers['Cache-Control'])
            self.assertIn('attachment',response.headers['Content-Disposition'])
            pdf = PdfReader(BytesIO(response.data))
            text = '\n'.join(p.extract_text() for p in pdf.pages)
            self.assertIn('Reporte administrativo',text)
            self.assertIn('Situación actual',text)
            for private in ('SECRET', 'PrivatePerson', 'user@example.test'):
                self.assertNotIn(private,text)
                self.assertNotIn(private.encode(),page.data)
            response.close()

    def test_permissions_invalid_and_empty_period(self):
        for route in ('/admin','/admin/reporte.pdf'):
            for query in ('periodo=invalid','fecha=2026-02-30','periodo=anio&fecha=9999-01-01'):
                self.assertEqual(self.client.get(route+'?'+query).status_code,400)
        response = self.client.get('/admin/reporte.pdf?periodo=mes&fecha=2025-01-01')
        self.assertEqual(response.status_code,200)
        response.close()
        self.signin(self.user)
        self.assertEqual(self.client.get('/admin/reporte.pdf').status_code,403)
        self.assertEqual(self.app.test_client().get('/admin/reporte.pdf').status_code,302)
