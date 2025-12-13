# app/__init__.py
from flask import Flask
from flask import redirect, request, url_for
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
    login.login_message = 'Please sign in to access this page.'

    # 3. Importar modelos AQUÍ (dentro de la función) evita el error circular
    from .models import User 

    @login.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Registrar Blueprints
    from .main.routes import bp as main_bp
    from .projects.routes import bp as projects_bp
    from .blog import bp as blog_bp
    from .auth.routes import bp as auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    @app.get('/proyectos')
    @app.get('/proyectos/')
    def legacy_projects_root():
        return redirect(url_for('projects.projects_home'), code=301)

    @app.get('/proyectos/<path:subpath>')
    def legacy_projects(subpath: str):
        query = f"?{request.query_string.decode()}" if request.query_string else ""
        return redirect(f"/projects/{subpath}{query}", code=301)

    return app
