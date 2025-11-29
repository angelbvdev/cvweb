from flask import Blueprint, render_template, send_from_directory, current_app, request, flash, redirect, url_for
import os
from flask_mail import Message
from app import mail
from app.extensions import db

bp = Blueprint('main', __name__, template_folder='templates')

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Inicio')

@bp.route('/sobre-mi')
def about():
    return render_template('about.html', title='Sobre Mí')

@bp.route('/contacto', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')     # El correo de la persona que escribe
        subject = request.form.get('subject')
        message_body = request.form.get('message')

        # Creamos el mensaje
        # Ponemos tu correo como sender para que Gmail no lo bloquee como spam
        msg = Message(subject=f"Nuevo contacto web: {subject}",
                      recipients=['angelbv.dev@gmail.com']) 
        
        # En el cuerpo ponemos quién lo mandó
        msg.body = f"""
        Has recibido un nuevo mensaje desde tu portafolio.
        
        Nombre: {name}
        Correo: {email}
        Asunto: {subject}
        
        Mensaje:
        {message_body}
        """
        msg.reply_to = email

        try:
            mail.send(msg)
            flash(f'¡Gracias {name}! Tu mensaje ha sido enviado exitosamente.', 'success')
        except Exception as e:
            print(f"Error enviando correo: {e}")
            flash('Hubo un error al enviar el mensaje. Inténtalo más tarde.', 'danger')
        
        return redirect(url_for('main.contact'))

    return render_template('contact.html', title='Contáctame')

@bp.route('/descargar-cv')
def download_cv():
    path = os.path.join(current_app.root_path, 'static', 'documents')
    return send_from_directory(path, 'cv_angel.pdf', as_attachment=True)


@bp.route('/habilidades')
def skills():
    tech_skills = {
        'Lenguajes': [
            {'name': 'Python', 'level': 90},
            {'name': 'SQL', 'level': 80},
            {'name': 'JavaScript', 'level': 60},
            {'name': 'C#', 'level': 50}
        ],
        'Data Science & AI': [
            {'name': 'Pandas / NumPy', 'level': 85},
            {'name': 'Machine Learning (Scikit-learn)', 'level': 75},
            {'name': 'Stable Diffusion / LoRA', 'level': 80},
            {'name': 'Data Visualization', 'level': 70}
        ],
        'Herramientas & Cloud': [
            {'name': 'Git / GitHub', 'level': 85},
            {'name': 'Docker', 'level': 60},
            {'name': 'Azure (Fundamentals)', 'level': 50},
            {'name': 'Linux (Ubuntu)', 'level': 75}
        ]
    }
    return render_template('skills.html', title='Mis Habilidades', skills=tech_skills)