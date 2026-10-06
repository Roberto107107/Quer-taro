"""Run locally with python app.py, or use flask --app app:create_app."""
from app import create_app
from app.security import LocalRequestHandler

if __name__ == "__main__":
    app = create_app()
    if app.config['PRODUCTION']:
        raise RuntimeError('Usa python serve.py para producción detrás de HTTPS.')
    app.run(debug=False, request_handler=LocalRequestHandler)
