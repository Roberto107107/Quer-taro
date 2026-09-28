"""Register routes while retaining the original template endpoint names."""
def register_routes(app):
    from routes import auth, usuarios, publicaciones, convocatorias, chat, admin, acuerdos
    for module in (auth, usuarios, publicaciones, convocatorias, chat, admin, acuerdos):
        module.register(app)
