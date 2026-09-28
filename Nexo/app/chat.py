"""Private conversation storage."""
from app import get_db

def conversation(user_id, other_id):
    return get_db().execute(
        """SELECT * FROM mensajes WHERE (remitente_id=? AND destinatario_id=?)
        OR (remitente_id=? AND destinatario_id=?) ORDER BY id""",
        (user_id, other_id, other_id, user_id)).fetchall()
