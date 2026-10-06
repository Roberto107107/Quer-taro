import io
from pathlib import Path
import tempfile
import unittest
from app import create_app, get_db
from app.usuario import create_user, verification_token

class NexoTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-only",
                               "DATABASE": str(Path(self.temp.name) / "test.sqlite"),
                               "UPLOAD_FOLDER": str(Path(self.temp.name) / "uploads")})
        self.client = self.app.test_client()
        with self.app.app_context():
            self.admin_id = create_user("Admin", "Nexo", "admin@example.com", "password1234", rol="admin", verificado=1)
            self.user_id = create_user("Ana", "Nexo", "ana@example.com", "password1234", verificado=1)
            self.other_id = create_user("Luis", "Nexo", "luis@example.com", "password1234", verificado=1)

    def tearDown(self):
        self.temp.cleanup()

    def post(self, path, data=None, **kwargs):
        self.client.get("/login")
        with self.client.session_transaction() as session:
            token = session["csrf"]
        return self.client.post(path, data={"csrf_token": token, **(data or {})}, **kwargs)

    def login(self, correo="admin@example.com"):
        return self.post("/login", {"correo": correo, "password": "password1234"})

    def test_application_decisions_notify_only_applicant_once(self):
        with self.app.app_context():
            db = get_db()
            call_id = db.execute("INSERT INTO convocatorias(titulo,contenido,area,lugar,inicio,fin,autor_id) VALUES('Becas','Detalle','TI','Sede','2020-01-01T10:00','2099-01-01T10:00',?)", (self.admin_id,)).lastrowid
            for uid in (self.user_id, self.other_id):
                db.execute('INSERT INTO postulaciones(usuario_id,convocatoria_id) VALUES(?,?)', (uid, call_id))
            db.commit()
        path = f'/admin/convocatorias/{call_id}/postulantes/{self.user_id}/resolver'
        self.login('ana@example.com')
        self.assertEqual(self.post(path, {'estado': 'aceptada'}).status_code, 403)
        self.post('/logout')
        self.login()
        self.assertEqual(self.client.post(path, data={'estado': 'aceptada'}).status_code, 400)
        self.assertEqual(self.post(path, {'estado': 'invalid'}).status_code, 400)
        self.assertEqual(self.post(path, {'estado': 'aceptada'}).status_code, 302)
        self.assertEqual(self.post(path, {'estado': 'aceptada'}).status_code, 409)
        self.assertEqual(self.post(path, {'estado': 'rechazada'}).status_code, 409)
        other_path = f'/admin/convocatorias/{call_id}/postulantes/{self.other_id}/resolver'
        self.assertEqual(self.post(other_path, {'estado': 'rechazada'}).status_code, 302)
        missing_path = f'/admin/convocatorias/{call_id}/postulantes/{self.admin_id}/resolver'
        self.assertEqual(self.post(missing_path, {'estado': 'aceptada'}).status_code, 404)
        self.assertEqual(self.client.get(f'/admin/convocatorias/{call_id}/postulantes').status_code, 200)
        with self.app.app_context():
            db = get_db()
            messages = db.execute('SELECT * FROM mensajes ORDER BY id').fetchall()
            self.assertEqual(len(messages), 2)
            for message, uid, state in zip(messages, (self.user_id, self.other_id), ('aceptada', 'rechazada')):
                self.assertEqual(message['destinatario_id'], uid)
                self.assertEqual(message['remitente_id'], self.admin_id)
                self.assertEqual(message['leido'], 0)
                self.assertIn(f'Tu postulación fue {state}', message['contenido'])
                self.assertIn('Becas', message['contenido'])
                row = db.execute('SELECT * FROM postulaciones WHERE usuario_id=?', (uid,)).fetchone()
                self.assertEqual(row['estado'], state)
                self.assertEqual(row['revisado_por'], self.admin_id)
                self.assertTrue(row['revisado'])
        self.post('/logout')
        self.login('ana@example.com')
        self.assertIn('Postulación aceptada'.encode(), self.client.get('/inicio').data)
        chat = self.client.get(f'/mensajes?usuario={self.admin_id}').data
        self.assertIn('Tu postulación fue aceptada'.encode(), chat)
        self.assertNotIn('Tu postulación fue rechazada'.encode(), chat)
        self.post('/logout')
        self.login('luis@example.com')
        self.assertIn('Postulación rechazada'.encode(), self.client.get('/inicio').data)

    def test_registration_verification_and_authentication(self):
        result = self.post("/registro", {"nombre":"Eva", "apellidos":"Sol", "correo":"eva@example.com",
                           "password":"longpassword", "confirmacion":"longpassword", "area":"TI", "puesto":"Analista"})
        self.assertEqual(result.status_code, 302)
        result = self.post("/login", {"correo":"eva@example.com", "password":"longpassword"})
        self.assertIn("pendiente".encode(), result.data)
        with self.app.app_context():
            user = get_db().execute("SELECT * FROM usuarios WHERE correo='eva@example.com'").fetchone()
            self.assertNotEqual(user["password"], "longpassword")
            token = verification_token(user)
        self.assertEqual(self.client.get("/verificar/" + token).status_code, 200)
        self.assertEqual(self.post("/verificar/" + token).status_code, 302)
        self.assertEqual(self.post("/login", {"correo":"eva@example.com", "password":"longpassword"}).status_code, 302)
        self.assertEqual(self.client.get("/inicio").status_code, 200)
        self.assertEqual(self.client.get("/verificar/invalid").status_code, 400)

    def test_permissions_csrf_and_session_revocation(self):
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self.assertEqual(self.client.post("/login", data={}).status_code, 400)
        self.login("ana@example.com")
        for url in ("/admin", "/admin/publicaciones", "/admin/convocatorias", "/admin/usuarios"):
            self.assertEqual(self.client.get(url).status_code, 403)
            if url != "/admin":
                self.assertEqual(self.post(url).status_code, 403)
        with self.app.app_context():
            get_db().execute("UPDATE usuarios SET activo=0 WHERE id=?", (self.user_id,))
            get_db().commit()
        self.assertEqual(self.client.get("/perfil").status_code, 302)

    def test_all_pages_render_and_admin_cannot_lock_self_out(self):
        self.login()
        self.assertEqual(self.client.get('/inicio').location, '/admin')
        for url in ("/admin", "/admin/publicaciones", "/admin/convocatorias", "/admin/usuarios",
                    "/personas", "/perfil", "/convocatorias", "/mensajes", "/documentos"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.post("/admin/usuarios", {"usuario_id":self.admin_id, "rol":"usuario"})
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.post("/logout")
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_publication_crud_and_visibility(self):
        self.login()
        viewer = self.app.test_client()
        viewer.get('/login')
        with viewer.session_transaction() as session:
            token = session['csrf']
        viewer.post('/login', data={'correo': 'ana@example.com', 'password': 'password1234', 'csrf_token': token})
        values = {"titulo":"Comunicado de prueba", "contenido":"Texto completo <script>alert(1)</script>",
                  "tipo":"Aviso", "estado":"draft", "fecha":"2020-01-01", "vencimiento":""}
        self.assertEqual(self.post("/admin/publicaciones", values).status_code, 302)
        self.assertNotIn(b"Comunicado de prueba", viewer.get("/inicio").data)
        with self.app.app_context():
            post_id = get_db().execute("SELECT id FROM publicaciones").fetchone()[0]
        values["estado"] = "published"
        self.assertEqual(self.post(f"/admin/publicaciones?editar={post_id}", values).status_code, 302)
        page = viewer.get("/inicio").data
        self.assertIn(b"Comunicado de prueba", page)
        self.assertIn(b"&lt;script&gt;", page)
        values["fecha"] = "2999-01-01"
        self.post(f"/admin/publicaciones?editar={post_id}", values)
        self.assertNotIn(b"Comunicado de prueba", viewer.get("/inicio").data)
        values.update(fecha="2020-01-01", vencimiento="2020-01-02")
        self.post(f"/admin/publicaciones?editar={post_id}", values)
        self.assertNotIn(b"Comunicado de prueba", viewer.get("/inicio").data)
        self.assertEqual(self.post(f"/admin/publicaciones/{post_id}/eliminar").status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT count(*) FROM publicaciones WHERE archivado=0").fetchone()[0], 0)

    def test_role_home_and_creation_menu(self):
        self.assertEqual(self.login().location, '/admin')
        self.assertEqual(self.client.get('/').location, '/admin')
        for path in ('/admin', '/documentos', '/perfil'):
            page = self.client.get(path).data
            self.assertIn(b'admin-workspace', page)
            self.assertIn(b'create-menu', page)
            self.assertNotIn(b'Ir al panel de usuario', page)
            self.assertNotIn(b'class="nav-center"', page)
        self.assertIn(b'<option selected>Comunicado</option>', self.client.get('/admin/publicaciones?tipo=Comunicado').data)
        self.post('/logout')
        self.assertEqual(self.login('ana@example.com').location, '/inicio')
        self.assertNotIn(b'create-menu', self.client.get('/inicio').data)

    def test_feed_order_and_persistent_acknowledgments(self):
        with self.app.app_context():
            db = get_db()
            for title, day in [('Anterior', '2020-01-01'), ('Reciente', '2020-02-01')]:
                db.execute("INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,autor_id) VALUES(?,?,'Comunicado','published',?,?)", (title, 'Contenido', day, self.admin_id))
            db.execute("INSERT INTO convocatorias(titulo,contenido,area,lugar,inicio,fin,autor_id) VALUES('Convocatoria nueva','Contenido','TI','Sala','2999-01-01T10:00','2999-01-02T10:00',?)", (self.admin_id,))
            db.commit()
        self.login('ana@example.com')
        page = self.client.get('/inicio').data
        self.assertLess(page.index(b'Convocatoria nueva'), page.index(b'Reciente'))
        self.assertLess(page.index(b'Reciente'), page.index(b'Anterior'))
        self.assertEqual(self.client.post('/enterado/publicacion/1').status_code, 400)
        for path in ('/enterado/publicacion/1', '/enterado/publicacion/1', '/enterado/convocatoria/1'):
            self.assertEqual(self.post(path).status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM enterados_publicaciones').fetchone()[0], 1)
            self.assertEqual(get_db().execute('SELECT count(*) FROM enterados_convocatorias').fetchone()[0], 1)
        self.assertEqual(self.client.get('/inicio').data.count(b'class="acknowledged"'), 2)
        self.post('/logout')
        self.login('luis@example.com')
        self.assertNotIn(b'class="acknowledged"', self.client.get('/inicio').data)
        self.post('/logout')
        self.login('ana@example.com')
        self.assertEqual(self.client.get('/inicio').data.count(b'class="acknowledged"'), 2)

    def test_acknowledgment_rejects_hidden_content_and_admin(self):
        with self.app.app_context():
            db = get_db()
            for state, day, end in [('draft','2020-01-01',None),('published','2999-01-01',None),('published','2020-01-01','2020-02-01')]:
                db.execute('INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,vencimiento,autor_id) VALUES(?,?,?,?,?,?,?)', ('Oculta','Texto','Aviso',state,day,end,self.admin_id))
            db.commit()
        self.login('ana@example.com')
        for post_id in (1,2,3,999):
            self.assertEqual(self.post(f'/enterado/publicacion/{post_id}').status_code, 404)
        self.assertEqual(self.post('/enterado/invalido/1').status_code, 404)
        self.post('/logout')
        self.login()
        self.assertEqual(self.post('/enterado/publicacion/1').status_code, 403)

    def test_unified_feed_documents_and_acknowledgment(self):
        with self.app.app_context():
            db = get_db()
            doc_id = db.execute('INSERT INTO documentos(nombre,archivo,autor_id) VALUES(?,?,?)',
                                ('Circular.pdf','fixture.pdf',self.admin_id)).lastrowid
            db.commit()
        self.login('ana@example.com')
        page = self.client.get('/inicio').data
        self.assertIn(b'Circular.pdf', page)
        self.assertIn(b'class="institutional-feed"', page)
        self.assertIn(f'/documentos/{doc_id}'.encode(), page)
        self.assertNotIn(b'href="/documentos"', page)
        self.assertNotIn(b'href="/convocatorias"', page)
        self.assertNotIn(b'quick-links', page)
        for _ in range(2):
            self.assertEqual(self.post(f'/enterado/documento/{doc_id}').status_code, 302)
        self.assertIn(b'class="acknowledged"', self.client.get('/inicio').data)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM enterados_documentos').fetchone()[0], 1)
        self.post('/logout')
        self.login('luis@example.com')
        self.assertNotIn(b'class="acknowledged"', self.client.get('/inicio').data)
        self.assertEqual(self.post('/enterado/documento/999').status_code, 404)
        with self.app.app_context():
            db = get_db()
            db.execute('DELETE FROM documentos WHERE id=?', (doc_id,))
            db.commit()
            self.assertEqual(db.execute('SELECT count(*) FROM enterados_documentos').fetchone()[0], 0)

    def image_upload(self, color='blue'):
        from PIL import Image
        image = io.BytesIO()
        Image.new('RGB', (32,24), color).save(image, format='PNG')
        image.seek(0)
        return (image, 'imagen.png')

    def test_publication_image_upload_replace_remove_and_permissions(self):
        self.login()
        data = {'titulo':'Con imagen', 'contenido':'Texto', 'tipo':'Comunicado',
                'estado':'published','fecha':'2020-01-01'}
        self.assertEqual(self.post('/admin/publicaciones', {**data,'imagen':self.image_upload()}).status_code, 302)
        with self.app.app_context():
            row = get_db().execute('SELECT * FROM publicaciones').fetchone()
            post_id, filename = row['id'], row['imagen']
        folder = Path(self.temp.name) / 'uploads' / 'imagenes'
        self.assertTrue((folder / filename).exists())
        url = f'/contenido/publicacion/{post_id}/imagen'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/webp')
        response.close()
        self.assertEqual(self.post(f'/admin/publicaciones?editar={post_id}', {**data,'imagen':self.image_upload('red')}).status_code, 302)
        self.assertFalse((folder / filename).exists())
        self.post('/logout')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.login('ana@example.com')
        self.assertIn(url.encode(), self.client.get('/inicio').data)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        with self.app.app_context():
            get_db().execute("UPDATE publicaciones SET estado='draft' WHERE id=?", (post_id,))
            get_db().commit()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.post('/logout')
        self.login()
        self.post(f'/admin/publicaciones?editar={post_id}', {**data,'quitar_imagen':'1'})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(list(folder.iterdir()), [])

    def test_image_validation_and_call_deletion_cleanup(self):
        self.login()
        data = {'titulo':'Curso con imagen','contenido':'Texto','area':'TI','lugar':'Sala',
                'inicio':'2999-01-01T10:00','fin':'2999-01-02T10:00'}
        for payload in [b'<script>invalid</script>', b'x' * (5*1024*1024+1)]:
            self.assertEqual(self.post('/admin/convocatorias', {**data,'imagen':(io.BytesIO(payload),'imagen.png')}).status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM convocatorias').fetchone()[0], 0)
        self.assertEqual(self.post('/admin/convocatorias', {**data,'imagen':self.image_upload()}).status_code, 302)
        with self.app.app_context():
            row = get_db().execute('SELECT * FROM convocatorias').fetchone()
            call_id, name = row['id'], row['imagen']
        self.assertEqual(self.post(f'/admin/convocatorias?editar={call_id}', data).status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT imagen FROM convocatorias WHERE id=?',(call_id,)).fetchone()[0], name)
        self.post(f'/admin/convocatorias/{call_id}/eliminar')
        self.assertTrue((Path(self.temp.name) / 'uploads' / 'imagenes' / name).exists())

    def test_admin_acknowledgment_reports_all_content_types(self):
        with self.app.app_context():
            db = get_db()
            db.execute("INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,autor_id) VALUES('Comunicado','Texto','Comunicado','published','2020-01-01',?)", (self.admin_id,))
            db.execute("INSERT INTO convocatorias(titulo,contenido,area,lugar,inicio,fin,autor_id) VALUES('Curso','Texto','TI','Sala','2999-01-01T10:00','2999-01-02T10:00',?)", (self.admin_id,))
            db.execute("INSERT INTO documentos(nombre,archivo,autor_id) VALUES('Archivo.txt','archivo.txt',?)", (self.admin_id,))
            db.commit()
        self.login('ana@example.com')
        for kind in ('publicacion','convocatoria','documento'):
            self.assertEqual(self.post(f'/enterado/{kind}/1').status_code, 302)
            self.assertEqual(self.post(f'/enterado/{kind}/1').status_code, 302)
            self.assertEqual(self.client.get(f'/admin/enterados/{kind}/1').status_code, 403)
        self.post('/logout')
        self.login()
        for kind in ('publicacion','convocatoria','documento'):
            page = self.client.get(f'/admin/enterados/{kind}/1')
            self.assertEqual(page.status_code, 200)
            self.assertIn(b'ana@example.com', page.data)
            self.assertNotIn(b'luis@example.com', page.data)
            self.assertIn(b'<strong>1</strong>', page.data)
        for path in ('/admin/publicaciones','/admin/convocatorias','/documentos'):
            self.assertIn(b'Enterados (1)', self.client.get(path).data)
        self.assertEqual(self.client.get('/admin/enterados/invalido/1').status_code, 404)
        self.assertEqual(self.client.get('/admin/enterados/documento/999').status_code, 404)

    def test_application_persistence_permissions_and_admin_list(self):
        with self.app.app_context():
            db = get_db()
            call_id = db.execute("INSERT INTO convocatorias(titulo,contenido,area,lugar,inicio,fin,autor_id) VALUES('Inscripciones','Contenido','TI','Sala','2999-01-01T10:00','2999-01-02T10:00',?)", (self.admin_id,)).lastrowid
            db.commit()
        path = f'/convocatorias/{call_id}/postular'
        self.login('ana@example.com')
        self.assertIn(path.encode(), self.client.get('/inicio').data)
        self.assertEqual(self.client.post(path).status_code, 400)
        for _ in range(2):
            self.assertEqual(self.post(path).status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM postulaciones').fetchone()[0], 1)
            self.assertEqual(get_db().execute('SELECT count(*) FROM enterados_convocatorias').fetchone()[0], 0)
        self.assertNotIn(path.encode(), self.client.get('/inicio').data)
        self.assertEqual(self.client.get(f'/admin/convocatorias/{call_id}/postulantes').status_code, 403)
        self.post('/logout')
        self.login('ana@example.com')
        self.assertNotIn(path.encode(), self.client.get('/inicio').data)
        self.post('/logout')
        self.login('luis@example.com')
        self.assertIn(path.encode(), self.client.get('/inicio').data)
        self.post('/logout')
        self.login()
        self.assertEqual(self.post(path).status_code, 403)
        page = self.client.get(f'/admin/convocatorias/{call_id}/postulantes')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'ana@example.com', page.data)
        self.assertNotIn(b'luis@example.com', page.data)
        self.assertIn(b'Postulantes (1)', self.client.get('/admin/convocatorias').data)
        self.post(f'/admin/convocatorias/{call_id}/eliminar')
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM postulaciones').fetchone()[0], 1)
            self.assertEqual(get_db().execute('SELECT archivado FROM convocatorias WHERE id=?', (call_id,)).fetchone()[0], 1)

    def test_application_rejects_closed_and_missing_calls(self):
        with self.app.app_context():
            db = get_db()
            call_id = db.execute("INSERT INTO convocatorias(titulo,contenido,area,lugar,inicio,fin,autor_id) VALUES('Cerrada','Contenido','TI','Sala','2020-01-01T10:00','2020-01-02T10:00',?)", (self.admin_id,)).lastrowid
            db.commit()
        self.login('ana@example.com')
        self.assertEqual(self.post(f'/convocatorias/{call_id}/postular').status_code, 409)
        self.assertEqual(self.post('/convocatorias/999/postular').status_code, 404)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT count(*) FROM postulaciones').fetchone()[0], 0)

    def test_calls_validation_and_crud(self):
        self.login()
        data = {"titulo":"Curso", "contenido":"Contenido", "area":"TI", "lugar":"Sala",
                "inicio":"2026-10-10T10:00", "fin":"2026-10-09T10:00"}
        self.assertEqual(self.post("/admin/convocatorias", data).status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT count(*) FROM convocatorias").fetchone()[0], 0)
        data["fin"] = "2026-10-11T10:00"
        self.assertEqual(self.post("/admin/convocatorias", data).status_code, 302)
        with self.app.app_context():
            call_id = get_db().execute("SELECT id FROM convocatorias").fetchone()[0]
        self.assertIn(b"Curso", self.client.get("/convocatorias?q=curso").data)
        data["titulo"] = "Curso actualizado"
        self.post(f"/admin/convocatorias?editar={call_id}", data)
        self.assertIn(b"Curso actualizado", self.client.get("/convocatorias").data)
        self.assertEqual(self.post(f"/admin/convocatorias/{call_id}/eliminar").status_code, 302)

    def test_profile_and_private_messages(self):
        self.login("ana@example.com")
        self.post("/perfil", {"nombre":"Ana nueva", "apellidos":"Nexo", "area":"Sistemas",
                              "puesto":"Analista", "disponibilidad":"Ocupado"})
        self.assertIn(b"Ana nueva", self.client.get("/personas?q=Ana&area=Sistemas").data)
        self.assertEqual(self.post(f"/mensajes?usuario={self.admin_id}", {"contenido":"Mensaje privado"}).status_code, 302)
        self.post("/logout")
        self.login("luis@example.com")
        self.assertNotIn(b"Mensaje privado", self.client.get(f"/mensajes?usuario={self.admin_id}").data)
        self.post("/logout")
        self.login()
        self.assertIn(b"Mensaje privado", self.client.get(f"/mensajes?usuario={self.user_id}").data)
        self.post(f"/mensajes/{self.user_id}/leidos")
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT leido FROM mensajes").fetchone()[0], 1)

    def test_document_access_upload_download_delete(self):
        self.login("ana@example.com")
        self.assertEqual(self.post("/documentos", {"archivo":(io.BytesIO(b"test"),"test.txt")}).status_code, 403)
        self.post("/logout")
        self.login()
        self.assertEqual(self.post("/documentos", {"archivo":(io.BytesIO(b"test"),"test.txt")}).status_code, 302)
        with self.app.app_context():
            doc_id = get_db().execute("SELECT id FROM documentos").fetchone()[0]
        response = self.client.get(f"/documentos/{doc_id}")
        self.assertEqual(response.data, b"test")
        response.close()
        self.assertEqual(self.post(f"/documentos/{doc_id}/eliminar").status_code, 302)
        response = self.client.get(f"/documentos/{doc_id}")
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(len(list((Path(self.temp.name) / "uploads").iterdir())), 1)
        self.post('/logout')
        self.login('ana@example.com')
        self.assertEqual(self.client.get(f"/documentos/{doc_id}").status_code, 404)

    def test_database_survives_new_application(self):
        self.login("ana@example.com")
        self.post("/perfil", {"nombre":"Persistente", "apellidos":"", "area":"", "puesto":"", "disponibilidad":"Disponible"})
        second = create_app(dict(self.app.config))
        with second.app_context():
            self.assertEqual(get_db().execute("SELECT nombre FROM usuarios WHERE id=?", (self.user_id,)).fetchone()[0], "Persistente")

    def test_cli_admin_and_password_reset(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(args=["create-admin", "--correo", "cli@example.com", "--nombre", "CLI", "--password", "password1234"])
        self.assertEqual(result.exit_code, 0, result.output)
        result = runner.invoke(args=["reset-password", "cli@example.com", "--password", "newpassword123"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.post("/login", {"correo":"cli@example.com", "password":"newpassword123"}).status_code, 302)

if __name__ == "__main__":
    unittest.main()
