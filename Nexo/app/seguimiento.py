"""Migration, private notifications and an append-only administrative audit."""
from datetime import date, timedelta
import re
from flask import g, current_app
from app import get_db

SCHEMA = """
CREATE TABLE IF NOT EXISTS notificaciones (
 id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
 acuerdo_id INTEGER NOT NULL REFERENCES acuerdos(id), clave TEXT NOT NULL,
 texto TEXT NOT NULL, leida INTEGER NOT NULL DEFAULT 0,
 creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
 UNIQUE(usuario_id,clave)
);
CREATE INDEX IF NOT EXISTS notificaciones_usuario ON notificaciones(usuario_id,leida,id);
CREATE TABLE IF NOT EXISTS auditoria (
 id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES usuarios(id),
 accion TEXT NOT NULL, entidad TEXT NOT NULL, registro_id INTEGER,
 detalle TEXT NOT NULL DEFAULT '', creado TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE TRIGGER IF NOT EXISTS auditoria_no_update BEFORE UPDATE ON auditoria
 BEGIN SELECT RAISE(ABORT,'El historial es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS auditoria_no_delete BEFORE DELETE ON auditoria
 BEGIN SELECT RAISE(ABORT,'El historial es inmutable'); END;
"""


def migrate():
    db = get_db()
    schema = db.execute("SELECT sql FROM sqlite_master WHERE name='acuerdos'").fetchone()[0]
    if "'entregado'" not in schema:
        # Rebuild only the CHECK constraint. IDs, rows and child relationships survive.
        db.commit()
        # Preserve a consistent pre-migration copy before rebuilding a live table.
        if not current_app.testing:
            import sqlite3
            import secrets
            from contextlib import closing
            from pathlib import Path
            source = Path(current_app.config['DATABASE'])
            target = source.with_name(source.name + '.pre-revision-' + secrets.token_hex(4) + '.sqlite3')
            with closing(sqlite3.connect(target)) as snapshot:
                db.backup(snapshot)
        db.execute('PRAGMA foreign_keys=OFF')
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                new_schema = re.sub(r'CREATE TABLE\s+"?acuerdos"?', 'CREATE TABLE acuerdos_revision', schema, count=1, flags=re.IGNORECASE)
                new_schema = re.sub(r"'en_proceso'\s*,\s*'completado'", "'en_proceso','entregado','correcciones','completado'", new_schema, count=1)
                if new_schema == schema or "'entregado'" not in new_schema:
                    raise RuntimeError('Esquema de acuerdos no reconocido; se requiere migración manual.')
                db.execute(new_schema)
                db.execute('INSERT INTO acuerdos_revision SELECT * FROM acuerdos')
                db.execute('DROP TABLE acuerdos')
                db.execute('ALTER TABLE acuerdos_revision RENAME TO acuerdos')
                db.execute('CREATE INDEX acuerdos_participantes ON acuerdos(creador_id,responsable_id)')
                if db.execute('PRAGMA foreign_key_check').fetchall():
                    raise RuntimeError('La migración no conserva las relaciones; se revirtió.')
        finally:
            db.execute('PRAGMA foreign_keys=ON')
    with db:
        columns = {r['name'] for r in db.execute('PRAGMA table_info(acuerdos)')}
        if 'validado_por' not in columns:
            db.execute('ALTER TABLE acuerdos ADD COLUMN validado_por INTEGER REFERENCES usuarios(id)')
        for table in ('publicaciones', 'convocatorias', 'documentos'):
            cols = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
            if 'archivado' not in cols:
                db.execute(f'ALTER TABLE {table} ADD COLUMN archivado INTEGER NOT NULL DEFAULT 0')
    db.executescript(SCHEMA)


def audit(action, entity, record_id, detail='', actor_id=None):
    if actor_id is None:
        user = g.get('usuario')
        actor_id = user['id'] if user else None
    get_db().execute('INSERT INTO auditoria(actor_id,accion,entidad,registro_id,detalle) VALUES(?,?,?,?,?)',
                     (actor_id, action, entity, record_id, detail))


def notify(user_id, agreement_id, key, text):
    get_db().execute('INSERT OR IGNORE INTO notificaciones(usuario_id,acuerdo_id,clave,texto) VALUES(?,?,?,?)',
                     (user_id, agreement_id, key, text))


def notify_event(item, actor_id, event_id, label):
    recipient = item['responsable_id'] if actor_id == item['creador_id'] else item['creador_id']
    notify(recipient, item['id'], f'evento:{event_id}', f'Acuerdo #{item["id"]}: {label}.')


def notify_due(user_id=None, today=None):
    today = today or date.today()
    sql = "SELECT * FROM acuerdos WHERE estado IN ('propuesto','pendiente','en_proceso','correcciones') AND fecha_limite<=?"
    params = [(today + timedelta(days=2)).isoformat()]
    if user_id is not None:
        sql += ' AND (creador_id=? OR responsable_id=?)'
        params += [user_id,user_id]
    db = get_db()
    with db:
        for item in db.execute(sql, params).fetchall():
            kind = 'vencido' if item['fecha_limite'] < today.isoformat() else 'proximo'
            text = 'Fecha de entrega vencida' if kind == 'vencido' else 'La fecha de entrega está próxima'
            for uid in {item['creador_id'],item['responsable_id']}:
                notify(uid,item['id'],f'{kind}:{item["id"]}:{item["fecha_limite"]}',f'Acuerdo #{item["id"]}: {text} ({item["fecha_limite"]}).')
