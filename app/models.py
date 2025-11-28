from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String, nullable=False)
    long_description = db.Column(db.Text)
    technologies = db.Column(db.String)
    github_url = db.Column(db.String)
    website_url = db.Column(db.String)
    created_at = db.Column(db.DateTime)
    category_slug = db.Column(db.String(50), nullable=False)

    images = db.relationship("ProjectImage", backref="project", lazy=True)
    code = db.relationship("ProjectCode", backref="project", lazy=True)


class ProjectImage(db.Model):
    __tablename__ = "project_images"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    image_path = db.Column(db.String, nullable=False)
    caption = db.Column(db.String)


class ProjectCode(db.Model):
    __tablename__ = "project_code"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    file_name = db.Column(db.String)
    code_snippet = db.Column(db.Text)
    language = db.Column(db.String)
