from flask import Flask
from config import Config
from .models import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Registrar Blueprints
    from .main.routes import bp as main_bp
    from .projects.routes import bp as projects_bp
    app.register_blueprint(main_bp)  
    app.register_blueprint(projects_bp, url_prefix='/proyectos')

    return app
