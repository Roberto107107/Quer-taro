"""Call status is derived from dates, never a manually maintained label."""
from datetime import datetime
from app import get_db

def list_calls():
    now = datetime.now().isoformat(timespec="minutes")
    calls = []
    for row in get_db().execute("SELECT * FROM convocatorias WHERE archivado=0 ORDER BY inicio DESC"):
        item = dict(row)
        item["estado"] = "Próxima" if now < item["inicio"] else ("Finalizada" if now > item["fin"] else "Vigente")
        calls.append(item)
    return calls
