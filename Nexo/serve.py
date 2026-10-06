"""Production WSGI entry point. Bind only to a local HTTPS reverse proxy."""
from waitress import serve
from app import create_app

if __name__ == '__main__':
    app = create_app({'PRODUCTION': True})
    serve(app, host='127.0.0.1', port=5000, ident='', expose_tracebacks=False,
          max_request_body_size=app.config['MAX_CONTENT_LENGTH'], max_request_header_size=32768)
