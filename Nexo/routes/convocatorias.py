from flask import render_template, request
from app.convocatoria import list_calls
from app.usuario import login_required

def register(app):
    @app.get("/convocatorias")
    @login_required
    def convocatorias():
        query = request.args.get("q", "").casefold()
        estado = request.args.get("estado", "")
        calls = [item for item in list_calls() if
                 query in (item["titulo"] + " " + item["contenido"] + " " + item["area"]).casefold()
                 and (not estado or item["estado"] == estado)]
        return render_template("convocatorias/index.html", convocatorias=calls)
