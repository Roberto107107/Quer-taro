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
        for url in ("/inicio", "/admin", "/admin/publicaciones", "/admin/convocatorias", "/admin/usuarios",
                    "/personas", "/perfil", "/convocatorias", "/mensajes", "/documentos"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.post("/admin/usuarios", {"usuario_id":self.admin_id, "rol":"usuario"})
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.post("/logout")
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_publication_crud_and_visibility(self):
        self.login()
        values = {"titulo":"Comunicado de prueba", "contenido":"Texto completo <script>alert(1)</script>",
                  "tipo":"Aviso", "estado":"draft", "fecha":"2020-01-01", "vencimiento":""}
        self.assertEqual(self.post("/admin/publicaciones", values).status_code, 302)
        self.assertNotIn(b"Comunicado de prueba", self.client.get("/inicio").data)
        with self.app.app_context():
            post_id = get_db().execute("SELECT id FROM publicaciones").fetchone()[0]
        values["estado"] = "published"
        self.assertEqual(self.post(f"/admin/publicaciones?editar={post_id}", values).status_code, 302)
        page = self.client.get("/inicio").data
        self.assertIn(b"Comunicado de prueba", page)
        self.assertIn(b"&lt;script&gt;", page)
        values["fecha"] = "2999-01-01"
        self.post(f"/admin/publicaciones?editar={post_id}", values)
        self.assertNotIn(b"Comunicado de prueba", self.client.get("/inicio").data)
        values.update(fecha="2020-01-01", vencimiento="2020-01-02")
        self.post(f"/admin/publicaciones?editar={post_id}", values)
        self.assertNotIn(b"Comunicado de prueba", self.client.get("/inicio").data)
        self.assertEqual(self.post(f"/admin/publicaciones/{post_id}/eliminar").status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT count(*) FROM publicaciones").fetchone()[0], 0)

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
        self.assertEqual(self.client.get(f"/documentos/{doc_id}").status_code, 404)
        self.assertEqual(list((Path(self.temp.name) / "uploads").iterdir()), [])

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
