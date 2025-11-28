from flask import Blueprint, render_template, send_from_directory, current_app
import os

bp = Blueprint('main', __name__, template_folder='templates')

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Inicio')

@bp.route('/sobre-mi')
def about():
    return render_template('about.html', title='Sobre Mí')

@bp.route('/contacto')
def contact():
    return render_template('contact.html', title='Contáctame')

@bp.route('/descargar-cv')
def download_cv():
    path = os.path.join(current_app.root_path, 'static', 'documents')
    return send_from_directory(path, 'cv_angel.pdf', as_attachment=True)
