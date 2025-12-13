from flask import Blueprint, render_template, send_from_directory, current_app, request, flash, redirect, url_for
import os
from flask_mail import Message
from app import mail
from app.extensions import db

bp = Blueprint('main', __name__, template_folder='templates')

@bp.route('/')
@bp.route('/home')
def index():
    return render_template('index.html', title='Home')

@bp.route('/index')
def index_legacy():
    return redirect(url_for('main.index'), code=301)

@bp.route('/about')
def about():
    return render_template('about.html', title='About')

@bp.route('/sobre-mi')
def about_legacy():
    return redirect(url_for('main.about'), code=301)

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')  # El correo de la persona que escribe
        subject = request.form.get('subject')
        message_body = request.form.get('message')

        # Creamos el mensaje
        # Ponemos tu correo como sender para que Gmail no lo bloquee como spam
        msg = Message(subject=f"New portfolio contact: {subject}",
                      recipients=['angelbv.dev@gmail.com']) 
        
        # En el cuerpo ponemos quién lo mandó
        msg.body = f"""
        You have received a new message from your portfolio.
        
        Name: {name}
        Email: {email}
        Subject: {subject}
        
        Message:
        {message_body}
        """
        msg.reply_to = email

        try:
            mail.send(msg)
            flash(f'Thanks {name}! Your message has been sent successfully.', 'success')
        except Exception as e:
            print(f"Error enviando correo: {e}")
            flash('There was an error sending your message. Please try again later.', 'danger')
        
        return redirect(url_for('main.contact'))

    return render_template('contact.html', title='Contact')

@bp.route('/contacto')
def contact_legacy():
    return redirect(url_for('main.contact'), code=301)

@bp.route('/download-cv')
def download_cv():
    path = os.path.join(current_app.root_path, 'static', 'documents')
    filename = 'cv_angel.pdf'
    full_path = os.path.join(path, filename)
    if not os.path.exists(full_path):
        flash('Resume file is not available yet. You can still reach out via the contact form.', 'info')
        return redirect(url_for('main.resume'))
    return send_from_directory(path, filename, as_attachment=True)

@bp.route('/descargar-cv')
def download_cv_legacy():
    return redirect(url_for('main.download_cv'), code=301)

@bp.route('/resume')
def resume():
    return render_template('resume.html', title='Resume')
