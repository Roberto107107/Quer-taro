# NEXO · Comunicación institucional

Aplicación Flask con SQLite: registro y verificación de usuarios, inicio/cierre de sesión,
perfiles, directorio, publicaciones, convocatorias, mensajes privados y documentos.
El panel administrativo utiliza los datos almacenados, sin estadísticas ficticias.

## Ejecutar en Windows (PowerShell)

```powershell
cd Nexo
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app:create_app create-admin
.\.venv\Scripts\python.exe app.py
```

Abre http://127.0.0.1:5000. El comando de administrador solicita nombre, correo y
contraseña (mínimo 10 caracteres); no hay credenciales predeterminadas.
Los usuarios registrados quedan pendientes: el administrador puede verificarlos en
Administración → Usuarios. No se envían correos automáticamente.

También se puede generar un enlace de verificación (válido 24 horas) para entregarlo
después de comprobar la identidad:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app verification-link usuario@institucion.mx
.\.venv\Scripts\python.exe -m flask --app app:create_app reset-password usuario@institucion.mx
```

El segundo comando permite al operador restablecer una contraseña olvidada.

## Comportamiento

- Solo los administradores crean, editan y eliminan publicaciones y convocatorias,
  administran usuarios y suben/eliminan documentos.
- Las publicaciones en borrador, futuras o vencidas no aparecen en Inicio.
- El estado de las convocatorias se calcula por sus fechas, usando la hora local del servidor.
- Los mensajes son privados, se actualizan mediante el enlace de actualización y se
  marcan como leídos con el botón correspondiente. No hay WebSockets ni adjuntos de chat.
- Los documentos se comparten con usuarios autenticados y se descargan como archivos.
  Se admiten PDF, TXT, PNG, JPG, DOCX y XLSX hasta 10 MB por solicitud.
- Los formularios tienen protección CSRF; las contraseñas se almacenan como hashes.
- Los tiempos de creación y mensajes se muestran en UTC.

## Datos y configuración

SQLite, la clave de sesión y los documentos se guardan en `Nexo/instance/`,
excluido del repositorio. Respalda toda esa carpeta con el servidor detenido.
La base se inicializa automáticamente; no se insertan usuarios ni contenido ficticio.

Variables opcionales: `SECRET_KEY` (clave de sesión), `NEXO_DATABASE` (ruta SQLite),
`NEXO_HTTPS=1` (cookies exclusivas de HTTPS). Las variables se configuran en el
entorno; no se carga un archivo .env automáticamente. El servidor de desarrollo se
inicia sin depuración. Para publicar en internet se necesita un servidor WSGI, HTTPS
y una configuración operativa de respaldos, límites de acceso y distribución de correos.

## Pruebas

La revisión y configuración de seguridad, los resultados y los pendientes de
despliegue están documentados en [Nexo/SECURITY_REVIEW.md](Nexo/SECURITY_REVIEW.md).
Para producción, instalar `Nexo/requirements-production.txt` y usar `serve.py`
con `SECRET_KEY` y `NEXO_TRUSTED_HOSTS` en el entorno, detrás de HTTPS.
Las sesiones caducan a las ocho horas y se revocan al salir o restablecer la contraseña.

Desde `Nexo`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas utilizan una base temporal y no modifican los datos de la aplicación.

## Acuerdos desde el chat

En **Acuerdos → Reporte de acuerdos completados**, selecciona **Semanal** o
**Mensual**, una fecha dentro del periodo y **Descargar PDF**. La semana va de
lunes a domingo y el mes abarca el mes calendario completo. Se usa la fecha de
finalización del historial (UTC), no la fecha límite ni la de creación.
El PDF incluye total, título, compromiso, creador, responsable, fechas y nota de
cierre, con logo y páginas numeradas. Solo contiene acuerdos propios o asignados;
ser administrador no permite exportar acuerdos privados de terceros. Si no hay
resultados, el PDF lo indica. Registros antiguos sin evento de finalización no
se incluyen porque no se puede determinar su periodo de forma fiable.
Los PDF se generan en memoria y no se guardan en una carpeta pública.
Instala `Nexo/requirements.txt` para disponer del generador ReportLab; para ejecutar
las pruebas que leen los PDF instala también `Nexo/requirements-test.txt`.

En Mensajes, selecciona «Crear acuerdo» debajo de un mensaje. Define título,
descripción, responsable (un participante de esa conversación) y fecha de entrega.
El responsable ve un contador de propuestas en Acuerdos y puede aceptar o rechazar.
Al aceptar, el flujo es Pendiente → En proceso → Por revisar → Completado. El creador
confirma el cumplimiento o solicita correcciones; también puede cancelar un acuerdo
abierto. Entregar, revisar, rechazar o cancelar requiere una nota; cada transición
queda registrada en el historial. Las fechas vencidas se calculan en la hora local.

`/acuerdos` muestra únicamente los acuerdos creados por el usuario o asignados a él.
`/admin/acuerdos` muestra cifras globales sin mensajes, títulos, nombres ni notas.
Incluye notificaciones privadas de seguimiento y plazo; no envía correo ni adjuntos privados.
Archivo, historial, respaldos y automatización se describen en [Operación](Nexo/OPERACION.md).
Las tablas nuevas se crean al reiniciar el servidor, conservando los datos existentes.

## Estilos de la interfaz

La interfaz utiliza Bootstrap 5.3.8, guardado localmente en
`Nexo/static/vendor/bootstrap/` con su licencia MIT. No requiere CDN ni conexión
a internet para cargar sus estilos. El CSS distribuido se verificó con el SHA-384
publicado en https://getbootstrap.com/docs/5.3/getting-started/download/.

`base.html` carga Bootstrap, `acuerdos.css` y `bootstrap-theme.css`, en ese orden.
La personalización general y la distribución de los dos paneles se mantienen en
`bootstrap-theme.css`; el Inicio añade `home.css`. Las hojas antiguas sin uso
se eliminaron junto con el script puntual de integración de Bootstrap. Los formularios usan
`form-control` y `form-select`; botones, tarjetas y avisos usan componentes Bootstrap.

## Inicio por rol y confirmaciones de lectura

El dashboard administrativo permite filtrar por semana (lunes a domingo), mes o
año calendario y descargar **PDF** desde el mismo selector. Sus gráficas muestran
usuarios registrados, publicaciones/convocatorias/documentos creados, mensajes
enviados, postulaciones recibidas, enterados y acuerdos completados durante el
periodo (UTC). Las publicaciones creadas incluyen borradores; enterados son
confirmaciones explícitas, no visitas. La finalización se toma del historial.
El reporte anual agrupa los completados por mes; los otros, por día.

Se distinguen los eventos del periodo de la **situación actual**: estados globales
de acuerdos, usuarios activos/verificados, cuentas pendientes, acuerdos vencidos
y postulaciones pendientes. Los estados de postulaciones corresponden a las
recibidas en el periodo, evaluadas al consultar. No se reconstruyen estados pasados.
Solo administradores pueden usar `/admin/reporte.pdf`; no incluye conversaciones,
datos personales ni títulos/notas de acuerdos. Archivar conserva los registros y
los totales históricos. Dashboard y PDF utilizan las mismas consultas agregadas.

Administradores ingresan directamente a `/admin`; `/inicio` los redirige al panel
administrativo. Documentos y perfil mantienen la navegación de administración.
El menú desplegable «Crear» ofrece comunicado, convocatoria, aviso, evento,
información general y documento; el tipo elegido se preselecciona en el formulario.

Los usuarios ven en `/inicio` los 12 contenidos más recientes: publicaciones
publicadas y vigentes, convocatorias que aún no terminan y documentos. Se presentan
en un solo feed, sin accesos separados por tipo en el menú de usuario. Se ordenan
por fecha de publicación (o de creación en convocatorias y documentos).
«Enterado» registra una confirmación
individual persistente y no duplicable. No habilita acceso a borradores o contenidos
futuros/vencidos. Reinicia el servidor para registrar las nuevas rutas y tablas;
la inicialización conserva las cuentas y el contenido existentes.

## Imágenes y consulta de enterados

Publicaciones y convocatorias admiten una imagen JPG, PNG o WebP de hasta 5 MB
y 20 megapíxeles. Se puede añadir, reemplazar o quitar desde el formulario, con
vista previa. Pillow valida y vuelve a codificar el archivo como WebP, corrige
la orientación y limita sus dimensiones a 2400 píxeles. Las imágenes se almacenan
en `instance/uploads/imagenes/` y se sirven únicamente a usuarios autenticados;
los borradores, publicaciones futuras y contenido vencido son privados del administrador.
Al actualizar desde una versión anterior, instala `requirements.txt` y reinicia
el servidor para añadir las columnas de imagen sin eliminar los datos existentes.

En los listados administrativos de publicaciones, convocatorias y documentos,
«Enterados (n)» abre el listado de usuarios que confirmaron: nombre, correo, área
y fecha UTC. Solo administradores pueden consultar esas listas. La confirmación
proviene del botón «Enterado»; no se contabilizan visitas o visualizaciones automáticas.

## Postulaciones a convocatorias

En el feed, los usuarios pueden pulsar «Postularme» desde que la convocatoria está
publicada hasta su fecha de cierre (hora local). Se guarda una sola postulación
por cuenta y convocatoria; al volver, se muestra «Postulación registrada».
Postularse no marca automáticamente «Enterado» y no implica aceptación o selección.
El administrador puede aceptar o rechazar cada postulación pendiente desde la lista
de postulantes. La decisión se guarda y envía un mensaje privado al usuario con el
resultado y el nombre de la convocatoria, disponible en «Mensajes». El feed también
muestra el estado mientras la convocatoria siga visible. Las decisiones resueltas
no se repiten ni generan notificaciones duplicadas.
Administración → Convocatorias → «Postulantes (n)» muestra nombre, correo, área y
fecha UTC de registro. Solo administradores pueden consultar esa lista.
