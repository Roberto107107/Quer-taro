"""Private agreements and explicit, audited state transitions."""
from datetime import date
from app import get_db

STATES = {'propuesto': 'Por aceptar', 'pendiente': 'Pendiente',
          'en_proceso': 'En proceso', 'completado': 'Completado',
          'rechazado': 'Rechazado', 'cancelado': 'Cancelado'}
SCHEMA = """
CREATE TABLE IF NOT EXISTS acuerdos (
 id INTEGER PRIMARY KEY,
 mensaje_id INTEGER NOT NULL REFERENCES mensajes(id),
 creador_id INTEGER NOT NULL REFERENCES usuarios(id),
 responsable_id INTEGER NOT NULL REFERENCES usuarios(id),
 titulo TEXT NOT NULL, descripcion TEXT NOT NULL, fecha_limite TEXT NOT NULL,
 estado TEXT NOT NULL DEFAULT 'propuesto' CHECK(estado IN
 ('propuesto','pendiente','en_proceso','completado','rechazado','cancelado')),
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE TABLE IF NOT EXISTS acuerdo_historial (
 id INTEGER PRIMARY KEY, acuerdo_id INTEGER NOT NULL REFERENCES acuerdos(id),
 actor_id INTEGER NOT NULL REFERENCES usuarios(id), estado TEXT NOT NULL,
 nota TEXT NOT NULL DEFAULT '',
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE INDEX IF NOT EXISTS acuerdos_participantes ON acuerdos(creador_id,responsable_id);
"""

def actions(item, user_id):
    result = []
    if item['responsable_id'] == user_id:
        if item['estado'] == 'propuesto':
            result += [('pendiente', 'Aceptar acuerdo'), ('rechazado', 'Rechazar')]
        elif item['estado'] == 'pendiente':
            result += [('en_proceso', 'Iniciar trabajo')]
        elif item['estado'] == 'en_proceso':
            result += [('completado', 'Marcar completado')]
    if item['creador_id'] == user_id and item['estado'] in ('propuesto', 'pendiente', 'en_proceso'):
        result += [('cancelado', 'Cancelar acuerdo')]
    return result

def decorate(row):
    item = dict(row)
    item['vencido'] = item['fecha_limite'] < date.today().isoformat() and item['estado'] in ('propuesto', 'pendiente', 'en_proceso')
    return item

QUERY = """SELECT a.*, c.nombre AS creador, r.nombre AS responsable, r.area
FROM acuerdos a JOIN usuarios c ON c.id=a.creador_id
JOIN usuarios r ON r.id=a.responsable_id """

def pending_count(user_id):
    return get_db().execute("SELECT count(*) FROM acuerdos WHERE responsable_id=? AND estado='propuesto'", (user_id,)).fetchone()[0]
