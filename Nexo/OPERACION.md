# Seguimiento y operación de NEXO

## Acuerdos

El responsable acepta, inicia el trabajo y **entrega para revisión** con una nota.
Quien propuso el acuerdo confirma el cumplimiento o solicita correcciones con una nota.
Después de confirmar, puede agregar retroalimentación. Cada paso queda en el historial
privado de los participantes y genera una notificación para la contraparte.
Si una persona se asigna un acuerdo a sí misma, conserva ambos papeles: esa revisión
no constituye una validación independiente por otra persona.

Los acuerdos históricos completados se conservan, identificados sin validación
registrada. Los PDF se basan en la fecha UTC de cierre; entregar para revisión
todavía no cuenta como completado. El administrador ajeno al acuerdo ve estadísticas
agregadas, no conversaciones ni notas privadas.

Las notificaciones de plazo aparecen desde dos días antes y al vencer, una sola
vez por categoría y fecha de entrega. Se actualizan al iniciar sesión, abrir
Notificaciones y mediante `notify-due`. Son avisos internos, no correos ni mensajes externos.

## Archivo e historial

**Archivar** oculta publicaciones, convocatorias y documentos del usuario, conservando
adjuntos, enterados y postulaciones. En **Administración → Archivo** se restauran con
sus fechas y estado originales. Una convocatoria vencida no se reabre por restaurarla.
Los totales históricos no bajan al archivar. No se pueden recuperar registros que se
borraron antes de este cambio, salvo que exista un respaldo anterior.

**Historial** registra creación, edición, archivo, restauración, cambios de permisos
y resolución de postulaciones realizados desde estas rutas a partir de la actualización.
No contiene contraseñas ni texto de conversaciones. SQLite impide modificar o borrar
sus filas mediante triggers; quien administre directamente el archivo de base de datos
puede alterar el esquema. No es una bitácora externa inviolable ni reconstruye acciones previas.

## Respaldos y recuperación

Ejecutar desde la carpeta `Nexo`:

```powershell
.\.venv\Scripts\python.exe -m flask --app app.py backup
.\.venv\Scripts\python.exe -m flask --app app.py restore-backup RUTA_DEL_ZIP --destination RUTA_NUEVA
```

El ZIP contiene SQLite, los archivos de uploads y un manifiesto SHA-256. Comprueba
integridad de la base, relaciones y presencia de adjuntos referenciados. La restauración
verifica los hashes y exige una carpeta nueva; no sustituye la instancia activa. Las
sesiones restauradas se revocan. Los hashes detectan corrupción, no prueban autenticidad
frente a alguien que puede reemplazar también el manifiesto.

Para probar la copia, iniciar una instancia aislada con `NEXO_DATABASE` apuntando al
archivo `nexo.sqlite3` restaurado y `NEXO_UPLOAD_FOLDER` a sus `uploads`. Configurar la
clave de sesión por separado. Verificar inicio de sesión, un adjunto, un acuerdo y un
PDF antes de decidir una recuperación real. No ejecutar dos procesos contra una copia
que se esté reemplazando. Ante recuperación real, detener primero el servicio y
conservar la instancia anterior para poder revertir.

No se incluyen `.env` ni secretos en el ZIP. Guardar la configuración de producción en
un gestor de secretos. El ZIP sí contiene datos personales y hashes de contraseña:
limitar sus permisos y copiarlo a almacenamiento externo protegido. Un respaldo en
el mismo disco no protege ante pérdida del equipo. No hay eliminación automática por
antigüedad: establecer retención y vigilar espacio según las necesidades de operación.

Antes de reconstruir el esquema antiguo de acuerdos, la aplicación guarda una copia
SQLite `*.pre-revision-*.sqlite3` junto a la base (excepto en pruebas).

## Automatización en Windows

```powershell
.\.venv\Scripts\python.exe scripts/maintenance.py
.\scripts\install-maintenance.ps1 -At '08:00'
```

La tarea diaria ejecuta avisos y respaldo, sin almacenar contraseñas. Usa el Python del
entorno del proyecto. El equipo debe estar encendido y el usuario debe tener una sesión
abierta; recupera ejecuciones perdidas cuando sea posible. Consultar el resultado de la
tarea en el Programador de tareas y comprobar la fecha del último ZIP.
Si PowerShell restringe scripts, aplicar la política aprobada por el administrador;
estos scripts no cambian la política del equipo.

Para un servidor que opere sin sesión interactiva, configurar la tarea con una cuenta
de servicio autorizada y sus variables de entorno. Este instalador local no configura
esa cuenta ni un servicio remoto. Ejecutar periódicamente una restauración en una
carpeta nueva y verificar su contenido; que la tarea termine no sustituye ese ensayo.

## Antes de publicar

Usar `serve.py` y las dependencias de producción; configurar `NEXO_ENV=production`,
una `SECRET_KEY` aleatoria fuera del repositorio y `NEXO_TRUSTED_HOSTS`. Colocar el
servidor detrás de HTTPS y restringir el acceso directo al puerto interno.
Verificar en el dominio real las cookies Secure/HttpOnly/SameSite, CSP, los permisos
entre roles y las cabeceras del proxy. Ejecutar ZAP contra una instancia autorizada y
revisar sus hallazgos. HTTPS, proxy, recuperación del servidor definitivo y un nuevo
escaneo externo permanecen pendientes hasta disponer de ese entorno.
