"""Daily local maintenance, runnable directly with the project's Python."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.seguimiento import notify_due
from app.respaldo import backup

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        notify_due()
        result = backup(args.output_dir or Path(app.instance_path) / 'backups')
        print(f'Mantenimiento completado. Respaldo verificado: {result}')
