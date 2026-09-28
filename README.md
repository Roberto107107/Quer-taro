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

Desde `Nexo`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas utilizan una base temporal y no modifican los datos de la aplicación.

## Acuerdos desde el chat

En Mensajes, selecciona «Crear acuerdo» debajo de un mensaje. Define título,
descripción, responsable (un participante de esa conversación) y fecha de entrega.
El responsable ve un contador de propuestas en Acuerdos y puede aceptar o rechazar.
Al aceptar, el flujo es Pendiente → En proceso → Completado. El creador puede cancelar
un acuerdo abierto. Completar, rechazar o cancelar requiere una nota; cada transición
queda registrada en el historial. Las fechas vencidas se calculan en la hora local.

`/acuerdos` muestra únicamente los acuerdos creados por el usuario o asignados a él.
`/admin/acuerdos` muestra cifras globales sin mensajes, títulos, nombres ni notas.
No incluye avisos por correo, adjuntos privados ni recordatorios automáticos.
Las tablas nuevas se crean al reiniciar el servidor, conservando los datos existentes.
