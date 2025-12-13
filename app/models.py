from datetime import datetime
from .extensions import db 
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(512))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False) # Descripción corta
    long_description = db.Column(db.Text) # Markdown o HTML completo
    technologies = db.Column(db.String(200)) # Ej: "Python, Flask, Docker"
    github_url = db.Column(db.String(255))
    website_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # <--- Automático
    category_slug = db.Column(db.String(50), nullable=False) # Ej: "web-dev", "data-science"

    # Relaciones
    # cascade="all, delete" significa que si borras el proyecto, se borran sus imágenes y código
    images = db.relationship("ProjectImage", backref="project", lazy=True, cascade="all, delete-orphan")
    code = db.relationship("ProjectCode", backref="project", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Project {self.title}>'


class ProjectImage(db.Model):
    __tablename__ = "project_images"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255))


class ProjectCode(db.Model):
    __tablename__ = "project_code"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    file_name = db.Column(db.String(100)) # Ej: "app.py"
    code_snippet = db.Column(db.Text)
    language = db.Column(db.String(50)) # Ej: "python", "javascript"