"""Flask application entry point."""
from app import create_app
from app.security import LocalRequestHandler

# Instancia que utilizará Vercel/WSGI
app = create_app()

if __name__ == "__main__":
    if app.config["PRODUCTION"]:
        raise RuntimeError(
            "Usa python serve.py para producción detrás de HTTPS."
        )

    app.run(
        debug=False,
        request_handler=LocalRequestHandler
    )