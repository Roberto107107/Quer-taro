"""Unread message notifications."""
from app import get_db

def unread_count(user_id):
    return get_db().execute("SELECT count(*) FROM mensajes WHERE destinatario_id=? AND leido=0",
                            (user_id,)).fetchone()[0]
