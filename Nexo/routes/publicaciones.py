from flask import render_template
from app.publicacion import visible_publications
from app.usuario import login_required

def register(app):
    @app.get("/inicio")
    @login_required
    def inicio():
        return render_template("main/inicio.html", publicaciones=visible_publications())
