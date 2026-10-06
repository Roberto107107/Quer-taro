# Revisión de seguridad de NEXO — 2026-10-05

## Alcance y método

Se revisaron la fábrica Flask, configuración, arranque, todos los módulos `app/`
y `routes/`, las plantillas, ambos JavaScript, recursos CSS usados por la CSP,
dependencias, exclusiones Git y los cuatro commits disponibles localmente.
El directorio «Manual de Procesos Interno» es otro sitio estático, no servido por
las rutas de esta aplicación Flask; no se modificó. No se realizó un pentest de
una instalación pública ni se recibió el informe exportado de ZAP con sus payloads.

Se presentó el inventario antes de editar. La suite original pasó sus 26 pruebas.
No se modificaron plantillas, JavaScript, estilos, nombres de rutas ni permisos
funcionales. Se agregaron dos tablas de seguridad; no se borraron datos existentes.
Las pruebas usan bases, archivos y credenciales temporales, no cuentas reales.

## Hallazgos y tratamiento

| Hallazgo | Severidad contextual | Resultado |
|---|---|---|
| CSP ausente (ZAP 1) | Media, defensa faltante | CSP global restrictiva, comprobada en Chrome. |
| Clickjacking (ZAP 2) | Media | `frame-ancestors 'none'` y `X-Frame-Options: DENY`. |
| `Server` (ZAP 3) | Baja, información de plataforma | Eliminado en el arranque `python app.py` y en Waitress con `serve.py`; verificado mediante HTTP real. |
| `nosniff` ausente (ZAP 4) | Baja | Cabecera global, también en errores y archivos servidos por Flask. |
| Atributos controlables en login/registro (ZAP 5) | XSS no confirmado | Reflexión escapada dentro de `value="…"`; las pruebas no crean elementos ni eventos. No se desactiva autoescape. |
| Gestión de sesión detectada (ZAP 6) | Informativa por sí sola | Es normal identificar la cookie; se reforzó caducidad, revocación y configuración HTTPS. |
| Cookie copiada reutilizable tras logout/reset | Media, requiere obtener la cookie | Sesiones registradas y revocables en servidor. Logout revoca la sesión; reset revoca todas las del usuario. |
| Sin caducidad explícita apropiada | Media | Límite absoluto de 8 horas, sin renovación automática de la sesión autenticada. |
| Sin limitación de autenticación/registro | Media | Máximo 60 POST por IP y endpoint en 15 minutos, persistente en SQLite; respuesta 429. |
| CSRF no ASCII produce excepción | Baja | Comparación constante entre bytes UTF-8; token inválido devuelve 400. |
| Caché de información privada/referentes | Media/baja | `private, no-store` fuera de estáticos y `Referrer-Policy: no-referrer`. |
| Producción sin requisitos explícitos de clave/host/HTTPS | Media | Producción exige clave de al menos 32 caracteres y hosts permitidos, fuerza Secure y rechaza debug. |
| Documentos comprobados solo por extensión | Baja, solo sube el admin | Se comprueban firmas/contenedores, tamaños y formatos; se mantienen los tipos admitidos. |
| SECRET_KEY literal histórica en Git | Alta si se reutiliza en una instalación | Detectada en `Nexo/app.py`, commit `262098f0`. No se reproduce. Debe rotarse donde siga en uso. |

La clave histórica no coincide con la clave local actual ni con la variable de
entorno inspeccionada. `.env` estaba vacío. No se encontraron `.env`, `secret.key`
ni bases SQLite en el índice/historial consultado. Esto no demuestra ausencia de
secretos en ramas remotas no disponibles, copias, logs o respaldos. No se reescribió
el historial. Cambiar la clave histórica en código no la elimina de Git.

## CSP y XSS

```text
default-src 'none'; script-src 'self'; script-src-attr 'none';
style-src 'self'; style-src-attr 'none'; img-src 'self' data: blob:;
font-src 'self'; connect-src 'self'; form-action 'self';
frame-ancestors 'none'; base-uri 'none'; object-src 'none'
```

Bootstrap, CSS y JS se sirven localmente. `data:` se limita a imágenes para los
iconos SVG internos de Bootstrap; `blob:` permite previsualizar imágenes locales.
No se permiten scripts inline, `unsafe-eval`, estilos inline ni recursos de terceros.

En `_forms.html`, `request.form.get(name, value)` se refleja en el atributo `value`
entre comillas; `correo` en login y nombre/apellidos/correo/área/puesto en registro
son controlables. Las contraseñas y su confirmación se devuelven vacías. Jinja
escapa comillas y delimitadores: controlar el valor no permite crear atributos.
También se revisaron textos de publicaciones, mensajes, acuerdos, nombres,
`alt`, `aria-label`, consultas de búsqueda y opciones de formularios.
No se encontraron `|safe`, `Markup()`, `innerHTML`, `outerHTML`, `document.write`
ni evaluación de HTML/JavaScript proporcionado por usuarios en la app.
No se añadió sanitización destructiva: se conserva el texto y se escapa al renderizar.

La evidencia disponible es compatible con una alerta informativa/falso positivo
en esos atributos, no con XSS explotable. Hay que volver a probar el payload exacto
de ZAP para cerrar formalmente ese hallazgo.

## Autenticación, SQL y archivos

- Los hashes de contraseña siguen usando Werkzeug (scrypt por defecto en la versión
  auditada); no se almacenan contraseñas en claro. Registro exige 10–256 caracteres;
  login también limita el tamaño antes de ejecutar el hash.
- Login limpia la sesión y genera un token y CSRF nuevos. SQLite guarda únicamente
  el hash del token de autenticación, su propietario y caducidad. Las cookies
  anteriores a esta actualización requieren iniciar sesión otra vez.
- Logout, reset, desactivación, retirada de verificación y cambio de rol revocan
  las sesiones correspondientes. Los permisos se consultan en la base en cada petición.
- HttpOnly y SameSite=Lax se mantienen; Secure es obligatorio en producción.
- Todos los POST existentes siguen protegidos con CSRF; el control también cubre
  otros métodos no seguros. GET de verificación no activa la cuenta.
- Las consultas utilizan parámetros para los valores. Los identificadores SQL
  dinámicos provienen de constantes/listas internas; no se interpolan entradas HTTP.
  Bandit marca cuatro B608 en `routes/admin.py` y `routes/publicaciones.py` por esos
  identificadores: revisados como falsos positivos, sin silenciar la herramienta.
- Imágenes: decodificación y recodificación Pillow, límite 5 MB/20 megapíxeles,
  nombres aleatorios y acceso autenticado. Documentos: límite 10 MB, nombres
  aleatorios, descarga como adjunto y validación básica de PNG/JPEG/PDF/Office/TXT.
  Los ZIP de Office no se extraen; se limita el tamaño declarado y se rechazan macros VBA.
- La validación de formato NO certifica que PDF/Office/TXT estén libres de malware.
  Antivirus/CDR y cuotas globales de almacenamiento siguen siendo tareas operativas.

## Producción

Desde `Nexo`, instalar `requirements-production.txt` y ejecutar `python serve.py`
con el intérprete del entorno virtual. Este arranque activa el perfil de producción
y escucha solo en `127.0.0.1:5000`, detrás de un proxy HTTPS en la misma máquina.

Variables del proceso/gestor de secretos:

- `SECRET_KEY`: valor aleatorio exclusivo de la instalación (recomendado 32 bytes
  generados criptográficamente, representados como 64 caracteres hexadecimales).
  No escribirlo en scripts, repositorio ni ejemplos. Configurarlo mediante el
  gestor de secretos o el entorno del servicio y mantenerlo entre reinicios.
- `NEXO_TRUSTED_HOSTS`: dominios reales permitidos, separados por comas, sin esquema
  ni ruta. No usar comodines globales.
- `NEXO_ENV=production` para otros arranques WSGI/CLI con el perfil de producción.
- `NEXO_DATABASE`: ubicación protegida y persistente de SQLite, si se cambia.

`.env` no se carga automáticamente con estos entry points. El desarrollo local
con `python app.py` conserva la clave aleatoria de `instance/secret.key` y HTTP
local. No usar el servidor de desarrollo en producción. `flask run` no utiliza
el handler de `app.py` y puede seguir anunciando Werkzeug en `Server`.

El proxy debe terminar TLS, redirigir HTTP a HTTPS, conservar el Host permitido,
limitar cargas y ocultar su propia cabecera Server. HSTS se envía en producción
sin `includeSubDomains` ni preload. No se añade ProxyFix ni se confía ciegamente
en X-Forwarded-For: sin configuración adicional, todos los clientes detrás del
proxy comparten su IP para el límite. Configurar límites por cliente en el proxy
y revisar ese umbral en instalaciones con muchos usuarios/NAT.

Proteger con ACL de Windows (o permisos del sistema) `instance/`, clave, SQLite,
uploads y respaldos. El modo 0600 de creación de clave es útil en POSIX, pero no
sustituye ACL en Windows. No registrar cuerpos de login, cookies ni URLs completas
de verificación en logs de producción. Configurar rotación y acceso a logs.

## Verificación y reproducción

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-production.txt -r requirements-security.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/security_browser.py
.\.venv\Scripts\python.exe -m pip_audit -r requirements-production.txt
.\.venv\Scripts\python.exe -m pip_audit --local
.\.venv\Scripts\python.exe -m bandit -r app routes app.py config.py serve.py
.\.venv\Scripts\python.exe -m pip check
```

La prueba opcional de navegador requiere Chrome instalado. Las pruebas de
Waitress requieren `requirements-production.txt`; si falta, esa prueba se omite.
En esta revisión se instalaron y ejecutaron ambas, sin omisiones.

- Regresión: 26 pruebas originales correctas.
- Ejecución final conjunta: 36 pruebas correctas, sin omisiones. Persisten avisos
  `ResourceWarning` de archivos temporales en pruebas multipart existentes; no
  causaron fallos y no constituyen evidencia de una vulnerabilidad de producción.
- Seguridad: 10 pruebas adicionales correctas, incluyendo transporte HTTP real
  de Werkzeug/Waitress, XSS en atributos, errores, cookies, hosts, CSRF, SQL,
  revocación, caducidad, límites y documentos disfrazados.
- Chrome: nueve páginas privadas, acceso/salida de usuario/admin, estilos/logo,
  visor de imagen y preview blob; ninguna violación CSP ni error JavaScript.
- `pip-audit`: sin vulnerabilidades conocidas en la resolución de producción
  ni en el entorno instalado, a la fecha de revisión. No equivale a garantía
  frente a fallos desconocidos ni a análisis de todo el sistema operativo.
- `pip check`: sin dependencias incompatibles. `git diff --check`: sin errores
  de whitespace; avisos normales de conversión LF/CRLF en Windows.

Los informes JSON locales están en `instance/security-dependencies.json`,
`instance/security-installed-dependencies.json` y `instance/security-bandit.json`
(ignorados por Git). No se introdujeron claves ni cuentas reales en las pruebas.

## Pendientes y repetición de ZAP

No se pudo comprobar el TLS/proxy/dominio público porque no se proporcionó un
despliegue. Comprobar las seis alertas originales con sesiones autenticadas de
usuario y administrador. Revisar CSP, X-Frame-Options, nosniff y referente en
200/302/400/403/404/500 y descargas; Server también en errores emitidos por el
proxy o servidor antes de llegar a Flask. Esos errores externos necesitan sus
propias cabeceras. Revisar Secure/HttpOnly/SameSite en la URL HTTPS definitiva.

Repetir XSS con el payload original y verificar que permanezca como valor/texto,
no como atributo o elemento ejecutable. La detección de sesión puede continuar
como alerta informativa. Revisar permisos entre cuentas, CSRF y reproducción de
cookies después del logout/reset. Usar datos de prueba: el escaneo activo puede
crear, modificar o eliminar contenido y alcanzar el límite 429.

Quedan fuera de la corrección automática: rotación en instalaciones que usen la
clave histórica, limpieza coordinada del historial remoto, antivirus/CDR, cuotas,
TLS/proxy y protección distribuida frente a fuerza bruta. Los mensajes existentes
de registro permiten inferir si un correo está registrado; se conservaron para
no cambiar el comportamiento solicitado. Evaluar respuesta genérica/MFA según la
política institucional. No se afirma que ZAP completo haya quedado sin alertas.

## Archivos de esta corrección

Modificados: `.gitignore` raíz, `Nexo/.gitignore`, `Nexo/config.py`, `Nexo/app.py`,
`Nexo/app/__init__.py`, `Nexo/routes/auth.py`, `Nexo/routes/admin.py`,
`Nexo/tests/test_app.py`, `Nexo/tests/test_acuerdos.py` y `README.md` raíz.
Nuevos: `Nexo/app/security.py`, `Nexo/app/documento.py`, `Nexo/serve.py`,
`Nexo/requirements-production.txt`, `Nexo/requirements-security.txt`,
`Nexo/tests/test_security.py`, `Nexo/tests/security_browser.py` y este informe.
Los cambios visuales/funcionales que ya existían en el árbol de trabajo se conservaron.

Referencias: [Flask, seguridad](https://flask.palletsprojects.com/en/stable/web-security/),
[Waitress, configuración](https://docs.pylonsproject.org/projects/waitress/en/latest/arguments.html),
[pip-audit](https://pypi.org/project/pip-audit/).
