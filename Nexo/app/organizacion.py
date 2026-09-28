"""Organization areas derived from member profiles."""
from app import get_db

def areas():
    return [row[0] for row in get_db().execute(
        "SELECT DISTINCT area FROM usuarios WHERE activo=1 AND area<>'' ORDER BY area")]
