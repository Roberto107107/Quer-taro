"""Consistent backups and restore rehearsal to a new directory, never over live data."""
import hashlib
import json
import secrets
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
import click
from flask import current_app
from app import get_db


def validate_db(path):
    with closing(sqlite3.connect(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('La base restaurada no supera la comprobación de integridad.')


def safe_destination(path):
    resolved=Path(path).resolve()
    public=Path(current_app.static_folder).resolve()
    if resolved==public or public in resolved.parents:
        raise ValueError('Los respaldos no pueden guardarse en static/.')
    return resolved


def backup(destination):
    destination=safe_destination(destination)
    destination.mkdir(parents=True,exist_ok=True)
    name='nexo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)+'.zip'
    target=destination/name
    uploads=Path(current_app.config['UPLOAD_FOLDER']).resolve()
    manifest={}
    db=get_db()
    db.execute('BEGIN IMMEDIATE')
    try:
        with tempfile.TemporaryDirectory() as folder:
            snapshot=Path(folder)/'nexo.sqlite3'
            with closing(sqlite3.connect(current_app.config['DATABASE'])) as source, closing(sqlite3.connect(snapshot)) as copy:
                source.backup(copy)
            validate_db(snapshot)
            with ZipFile(target,'x',compression=ZIP_DEFLATED) as archive:
                files=[('nexo.sqlite3',snapshot)]
                if uploads.exists():
                    for path in uploads.rglob('*'):
                        if path.is_symlink():
                            raise ValueError('No se permiten enlaces simbólicos en uploads.')
                        if path.is_file():
                            files.append(('uploads/'+path.relative_to(uploads).as_posix(),path))
                for name,path in files:
                    data=path.read_bytes()
                    manifest[name]=hashlib.sha256(data).hexdigest()
                    archive.writestr(name,data)
                # Ensure every referenced asset is included, not just a successful ZIP.
                for table,column,prefix in [('documentos','archivo','uploads/'),('publicaciones','imagen','uploads/imagenes/'),('convocatorias','imagen','uploads/imagenes/')]:
                    for row in db.execute(f'SELECT {column} FROM {table} WHERE {column} IS NOT NULL'):
                        if prefix+row[0] not in manifest:
                            raise ValueError('Falta un archivo referenciado; el respaldo no está completo.')
                archive.writestr('manifest.json',json.dumps({'version':1,'files':manifest}))
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        db.rollback()
    return target


def restore(archive_path,destination):
    destination=safe_destination(destination)
    if destination.exists():
        raise ValueError('La restauración requiere un directorio nuevo; no sobrescribe datos.')
    with ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):
            raise ValueError('El respaldo contiene nombres duplicados.')
        manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('version')!=1 or set(names)!=(set(manifest['files'])|{'manifest.json'}) or 'nexo.sqlite3' not in names:
            raise ValueError('Manifiesto de respaldo inválido.')
        for name in manifest['files']:
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or not (name=='nexo.sqlite3' or name.startswith('uploads/')):
                raise ValueError('Ruta insegura en el respaldo.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        # Stage in the same parent. A failed verification leaves no partial destination.
        with tempfile.TemporaryDirectory(dir=destination.parent) as stage:
            for name,expected in manifest['files'].items():
                data=archive.read(name)
                if hashlib.sha256(data).hexdigest()!=expected:
                    raise ValueError('La suma de verificación del respaldo no coincide.')
                target=Path(stage)/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
            validate_db(Path(stage)/'nexo.sqlite3')
            with closing(sqlite3.connect(Path(stage)/'nexo.sqlite3')) as db:
                db.execute('DELETE FROM auth_sessions')
                db.commit()
            # Copy verified data; no restoration over a running instance is permitted.
            import shutil
            shutil.copytree(stage,destination)
    return destination


def register_commands(app):
    @app.cli.command('backup')
    @click.option('--output-dir',type=click.Path(path_type=Path),default=None)
    def backup_command(output_dir):
        try:
            path=backup(output_dir or Path(app.instance_path)/'backups')
        except (OSError,ValueError,sqlite3.Error) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f'Respaldo verificado: {path}')

    @app.cli.command('restore-backup')
    @click.argument('archive',type=click.Path(exists=True,path_type=Path))
    @click.option('--destination',required=True,type=click.Path(path_type=Path))
    def restore_command(archive,destination):
        try:
            restore(archive,destination)
        except (OSError,ValueError,sqlite3.Error) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo('Restauración comprobada en un directorio nuevo. No se modificó la instancia activa.')

    @app.cli.command('notify-due')
    def notify_due_command():
        from app.seguimiento import notify_due
        notify_due()
        click.echo('Avisos de vencimiento actualizados sin duplicados.')
