"""Optional real-browser CSP smoke test; uses only disposable data and credentials."""
from datetime import date
from io import BytesIO
from pathlib import Path
import secrets
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from playwright.sync_api import sync_playwright
from werkzeug.datastructures import FileStorage
from werkzeug.serving import make_server
from app import create_app, get_db
from app.usuario import create_user
from app.imagen import save_image
from app.security import LocalRequestHandler


def main():
    with tempfile.TemporaryDirectory() as folder:
        password = secrets.token_urlsafe(24)
        app = create_app({'TESTING': True, 'SECRET_KEY': secrets.token_hex(32),
            'DATABASE': str(Path(folder) / 'browser.sqlite'), 'UPLOAD_FOLDER': str(Path(folder) / 'uploads')})
        png = BytesIO()
        Image.new('RGB', (100, 160), '#4466aa').save(png, format='PNG')
        with app.app_context():
            admin = create_user('Review', '', 'admin@example.test', password, rol='admin', verificado=1)
            create_user('Review', '', 'user@example.test', password, verificado=1)
            filename = save_image(FileStorage(stream=BytesIO(png.getvalue()), filename='image.png'))
            get_db().execute('''INSERT INTO publicaciones(titulo,contenido,tipo,estado,fecha,autor_id,imagen)
                VALUES(?,?,?,'published',?,?,?)''', ('Browser review', 'Contenido', 'Aviso', date.today().isoformat(), admin, filename))
            get_db().commit()
        server = make_server('127.0.0.1', 0, app, request_handler=LocalRequestHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel='chrome', headless=True)
                page = browser.new_page()
                violations = []
                errors = []
                page.expose_function('recordViolation', lambda info: violations.append(info))
                page.add_init_script("document.addEventListener('securitypolicyviolation', e => window.recordViolation(e.violatedDirective + ':' + e.blockedURI));")
                page.on('pageerror', lambda error: errors.append(str(error)))
                base = f'http://127.0.0.1:{server.server_port}'
                for identity, routes in [('user', ['/inicio', '/mensajes', '/acuerdos', '/perfil', '/notificaciones']),
                                         ('admin', ['/admin', '/admin/convocatorias', '/admin/publicaciones', '/documentos', '/admin/acuerdos', '/admin/archivo', '/admin/historial', '/notificaciones'])]:
                    page.goto(base + '/login')
                    page.locator('[name=correo]').fill(identity + '@example.test')
                    page.locator('[name=password]').fill(password)
                    page.get_by_role('button', name='Iniciar sesión').click()
                    page.wait_for_url('**/inicio' if identity == 'user' else '**/admin')
                    for route in routes:
                        response = page.goto(base + route)
                        assert response.status == 200
                        assert page.locator('.institution-logo').first.evaluate('(img) => img.complete && img.naturalWidth > 0')
                        assert page.locator('body').evaluate('(el) => getComputedStyle(el).fontFamily').find('Segoe') >= 0
                        if route == '/acuerdos':
                            page.locator('#reporte-periodo').select_option('mes')
                            with page.expect_download() as download_info:
                                page.get_by_role('button', name='Descargar PDF').click()
                            download = download_info.value
                            target = Path(folder) / download.suggested_filename
                            download.save_as(target)
                            assert target.read_bytes().startswith(b'%PDF-')
                            assert download.suggested_filename.startswith('acuerdos-mes-')
                        if route == '/admin':
                            assert page.locator('.analytics-bars').count() == 3
                            page.locator('#admin-periodo').select_option('anio')
                            page.get_by_role('button', name='Ver estadísticas', exact=True).click()
                            page.wait_for_url('**/admin?periodo=anio&fecha=*')
                            with page.expect_download() as download_info:
                                page.get_by_role('button', name='Descargar PDF', exact=True).click()
                            download = download_info.value
                            target = Path(folder) / download.suggested_filename
                            download.save_as(target)
                            assert target.read_bytes().startswith(b'%PDF-')
                            assert download.suggested_filename.startswith('nexo-administracion-anio-')
                        if route == '/inicio':
                            page.locator('[data-expand-image]').click()
                            assert page.locator('#image-viewer').evaluate('(el) => el.open')
                            page.wait_for_function("document.querySelector('.image-viewer-full').naturalWidth > 0")
                            page.keyboard.press('Escape')
                            assert not page.locator('#image-viewer').evaluate('(el) => el.open')
                        if route == '/admin/publicaciones':
                            page.locator('#imagen').set_input_files({'name': 'image.png', 'mimeType': 'image/png', 'buffer': png.getvalue()})
                            page.wait_for_function("document.querySelector('#imagen-preview').naturalWidth > 0")
                    page.get_by_role('button', name='Salir', exact=True).click()
                assert not violations, violations
                assert not errors, errors
                browser.close()
                print('Chrome: 13 pages, authenticated flows, PDF download, local CSS/logo, full image and blob preview; no CSP violations or JS errors.')
        finally:
            server.shutdown()
            worker.join(timeout=5)
            server.server_close()


if __name__ == '__main__':
    main()
