"""Publication queries; drafts and scheduled/expired posts remain private."""
from datetime import date
from app import get_db

def visible_publications():
    today = date.today().isoformat()
    return get_db().execute(
        """SELECT p.*, u.nombre AS autor FROM publicaciones p JOIN usuarios u ON u.id=p.autor_id
        WHERE p.archivado=0 AND p.estado='published' AND p.fecha<=? AND (p.vencimiento IS NULL OR p.vencimiento>=?)
        ORDER BY p.fecha DESC,p.id DESC""", (today, today)).fetchall()
