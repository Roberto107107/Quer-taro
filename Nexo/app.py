"""Run locally with python app.py, or use flask --app app:create_app."""
from app import create_app

if __name__ == "__main__":
    create_app().run()
