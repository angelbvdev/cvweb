# app/__init__.py
from flask import Flask
from config import Config
from .extensions import db, mail, login, migrate # <--- 1. Importamos desde extensions

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 2. Inicializamos las extensiones
    db.init_app(app)
    mail.init_app(app)
    login.init_app(app)
    migrate.init_app(app, db)

    # Configuración de Login
    login.login_view = 'auth.login'
    login.login_message = 'Inicia sesión para acceder.'

    # 3. Importar modelos AQUÍ (dentro de la función) evita el error circular
    from .models import User 

    @login.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Registrar Blueprints
    from .main.routes import bp as main_bp
    from .projects.routes import bp as projects_bp
    from .auth.routes import bp as auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/proyectos')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
