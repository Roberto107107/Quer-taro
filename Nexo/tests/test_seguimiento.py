import sqlite3
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import unittest
import test_acuerdos as fixtures
from app import create_app, get_db
from app.seguimiento import notify_due, audit
from app.respaldo import backup, restore


class FollowupTest(unittest.TestCase):
    setUp = fixtures.AgreementTest.setUp
    tearDown = fixtures.AgreementTest.tearDown
    signin = fixtures.AgreementTest.signin
    post = fixtures.AgreementTest.post
    create = fixtures.AgreementTest.create

    def test_correction_review_and_private_notifications(self):
        self.create()
        self.signin(self.owner)
        for state in ('pendiente', 'en_proceso', 'entregado'):
            self.assertEqual(self.post('/acuerdos/1', {'estado': state, 'nota': 'Primera entrega'}).status_code, 302)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'completado', 'nota': 'Autoaprobar'}).status_code, 403)
        self.signin(self.creator)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'correcciones'}).status_code, 200)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'correcciones', 'nota': 'Falta un punto'}).status_code, 302)
        self.signin(self.owner)
        self.assertIn(b'Falta un punto', self.client.get('/acuerdos/1').data)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'entregado', 'nota': 'Punto corregido'}).status_code, 302)
        self.signin(self.creator)
        self.assertEqual(self.post('/acuerdos/1', {'estado': 'completado', 'nota': 'Revisado'}).status_code, 302)
        with self.app.app_context():
            db = get_db()
            item = db.execute('SELECT * FROM acuerdos').fetchone()
            self.assertEqual((item['estado'], item['validado_por']), ('completado', self.creator))
            self.assertEqual(db.execute('SELECT count(*) FROM acuerdo_historial').fetchone()[0], 7)
            notice = db.execute('SELECT id FROM notificaciones WHERE usuario_id=?', (self.owner,)).fetchone()[0]
        self.assertEqual(self.post(f'/notificaciones/{notice}/leida').status_code, 404)
        self.signin(self.owner)
        self.assertEqual(self.client.post(f'/notificaciones/{notice}/leida').status_code, 400)
        self.assertEqual(self.post(f'/notificaciones/{notice}/leida').status_code, 302)
        self.signin(self.admin)
        self.assertNotIn(b'Acuerdo #1', self.client.get('/notificaciones').data)
        self.assertEqual(self.post(f'/notificaciones/{notice}/leida').status_code, 404)

    def test_deadline_deduplication_and_audit_permissions(self):
        self.create()
        with self.app.app_context():
            db = get_db()
            notify_due()
            first = db.execute('SELECT count(*) FROM notificaciones').fetchone()[0]
            notify_due()
            self.assertEqual(db.execute('SELECT count(*) FROM notificaciones').fetchone()[0], first)
            self.assertEqual(first, 3)
            audit('prueba', 'publicacion', 1, actor_id=self.admin)
            db.commit()
            for sql in ('DELETE FROM auditoria', "UPDATE auditoria SET accion='alterado'"):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)
                db.rollback()
        self.assertEqual(self.client.get('/admin/historial').status_code, 403)
        self.signin(self.admin)
        self.assertIn(b'prueba', self.client.get('/admin/historial').data)

    def test_archive_restores_feed_and_preserves_acknowledgments(self):
        with self.app.app_context():
            db = get_db()
            db.execute("INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,autor_id) VALUES('Contenido conservado','Texto','Comunicado','published','2020-01-01',?)", (self.admin,))
            db.commit()
        self.assertEqual(self.post('/enterado/publicacion/1').status_code, 302)
        self.assertEqual(self.post('/admin/publicaciones/1/eliminar').status_code, 403)
        self.signin(self.admin)
        self.assertEqual(self.post('/admin/publicaciones/1/eliminar').status_code, 302)
        self.assertIn(b'Contenido conservado', self.client.get('/admin/archivo').data)
        self.signin(self.owner)
        self.assertNotIn(b'Contenido conservado', self.client.get('/inicio').data)
        self.assertEqual(self.post('/enterado/publicacion/1').status_code, 404)
        self.assertEqual(self.post('/admin/archivo/publicacion/1/restaurar').status_code, 403)
        self.signin(self.admin)
        self.assertEqual(self.post('/admin/archivo/publicacion/1/restaurar').status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM enterados_publicaciones').fetchone()[0], 1)
            self.assertEqual(get_db().execute('SELECT count(*) FROM auditoria').fetchone()[0], 2)
        self.signin(self.owner)
        self.assertIn(b'Contenido conservado', self.client.get('/inicio').data)

    def test_backup_restore_and_tampering(self):
        self.create()
        root = Path(self.temp.name)
        uploads = root / 'uploads'
        uploads.mkdir()
        (uploads / 'archivo.txt').write_text('Contenido verificado', encoding='utf-8')
        self.app.config['UPLOAD_FOLDER'] = str(uploads)
        with self.app.app_context():
            db = get_db()
            db.execute("INSERT INTO documentos(nombre,archivo,autor_id) VALUES('archivo.txt','archivo.txt',?)", (self.admin,))
            db.commit()
            archive = backup(root / 'backups')
            destination = restore(archive, root / 'restored')
            self.assertEqual((destination / 'uploads' / 'archivo.txt').read_bytes(), (uploads / 'archivo.txt').read_bytes())
            with closing(sqlite3.connect(destination / 'nexo.sqlite3')) as copy:
                self.assertEqual(copy.execute('SELECT count(*) FROM acuerdos').fetchone()[0], 1)
                self.assertEqual(copy.execute('SELECT count(*) FROM auth_sessions').fetchone()[0], 0)
            self.assertGreater(db.execute('SELECT count(*) FROM auth_sessions').fetchone()[0], 0)
            with self.assertRaises(ValueError):
                restore(archive, destination)
            tampered = root / 'tampered.zip'
            with ZipFile(archive) as source, ZipFile(tampered, 'w', ZIP_DEFLATED) as target:
                for name in source.namelist():
                    target.writestr(name, b'Alterado' if name == 'uploads/archivo.txt' else source.read(name))
            with self.assertRaises(ValueError):
                restore(tampered, root / 'invalid')
            self.assertFalse((root / 'invalid').exists())
            with self.assertRaises(ValueError):
                backup(Path(self.app.static_folder) / 'backups')

    def test_legacy_schema_migration_preserves_relationships(self):
        self.create()
        with self.app.app_context():
            db = get_db()
            schema = db.execute("SELECT sql FROM sqlite_master WHERE name='acuerdos'").fetchone()[0]
            legacy = schema.replace('CREATE TABLE acuerdos', 'CREATE TABLE legacy_acuerdos', 1).replace("'entregado','correcciones',", '')
            db.execute('PRAGMA foreign_keys=OFF')
            with db:
                db.execute(legacy)
                db.execute('INSERT INTO legacy_acuerdos SELECT * FROM acuerdos')
                db.execute('DROP TABLE acuerdos')
                db.execute('ALTER TABLE legacy_acuerdos RENAME TO acuerdos')
            db.execute('PRAGMA foreign_keys=ON')
        second = create_app(dict(self.app.config))
        with second.app_context():
            db = get_db()
            self.assertEqual(db.execute('SELECT count(*) FROM acuerdos').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM acuerdo_historial').fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            db.execute("UPDATE acuerdos SET estado='entregado'")
            db.commit()
