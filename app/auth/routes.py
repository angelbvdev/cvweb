from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Project, ProjectImage
from . import bp
import os
from werkzeug.utils import secure_filename
from flask import current_app

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('auth.dashboard')
        return redirect(next_page)
        
    return render_template('auth/login.html', title='Iniciar Sesión')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    # Obtenemos los proyectos ordenados por fecha (más reciente primero)
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('auth/dashboard.html', title='Panel de Control', projects=projects)

@bp.route('/create_project', methods=['POST'])
@login_required
def create_project():
    # 1. Recibir datos de texto (igual que antes)
    title = request.form.get('title')
    slug = request.form.get('slug')
    category = request.form.get('category')
    technologies = request.form.get('technologies')
    description = request.form.get('description')
    long_description = request.form.get('long_description')
    github_url = request.form.get('github_url')
    website_url = request.form.get('website_url')

    # 2. Crear el objeto Proyecto
    new_project = Project(
        title=title,
        slug=slug,
        category_slug=category,
        technologies=technologies,
        description=description,
        long_description=long_description,
        github_url=github_url,
        website_url=website_url
    )

    try:
        # 3. Guardamos el proyecto PRIMERO para generar el ID
        db.session.add(new_project)
        db.session.commit() 

        # 4. Procesar las Imágenes
        # 'images' debe coincidir con el name="images" del input HTML
        files = request.files.getlist('images') 
        
        for file in files:
            if file and file.filename != '':
                # Limpiamos el nombre del archivo (seguridad)
                filename = secure_filename(file.filename)
                
                # Guardamos el archivo físico en la carpeta static/uploads
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Guardamos la referencia en la Base de Datos
                # Aquí usamos new_project.id que acabamos de crear
                new_image = ProjectImage(
                    project_id=new_project.id, 
                    image_path=filename,
                    caption=title # Usamos el título como caption por defecto
                )
                db.session.add(new_image)
        
        # Hacemos commit de las imágenes
        db.session.commit()
        
        flash('¡Proyecto e imágenes creados exitosamente!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear proyecto: {str(e)}', 'danger')
        print(e) # Para ver el error en consola si pasa algo

    return redirect(url_for('auth.dashboard'))


@bp.route('/delete_project/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    project = Project.query.get_or_404(id)
    
    try:
        # === PASO 1: Borrar los archivos físicos (Imágenes) ===
        # Iteramos sobre las imágenes asociadas al proyecto
        for img in project.images:
            # Construimos la ruta completa del archivo
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], img.image_path)
            
            # Verificamos si el archivo existe para evitar errores
            if os.path.exists(file_path):
                os.remove(file_path) # <--- Aquí se borra la foto del disco
                print(f"Imagen eliminada: {file_path}")

        # === PASO 2: Borrar de la Base de Datos ===
        # Gracias al cascade="all, delete" en tu modelo, esto borrará 
        # también las filas en la tabla ProjectImage automáticamente.
        db.session.delete(project)
        db.session.commit()
        
        flash(f'El proyecto "{project.title}" y sus imágenes han sido eliminados.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'danger')
        print(e)

    return redirect(url_for('auth.dashboard'))


@bp.route('/edit_project/<int:id>', methods=['POST'])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)
    
    try:
        # 1. Actualizar datos de texto
        project.title = request.form.get('title')
        project.slug = request.form.get('slug')
        project.category_slug = request.form.get('category')
        project.technologies = request.form.get('technologies')
        project.description = request.form.get('description')
        project.long_description = request.form.get('long_description')
        project.github_url = request.form.get('github_url')
        project.website_url = request.form.get('website_url')

        # 2. Procesar NUEVAS imágenes (si las hay)
        files = request.files.getlist('images') 
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                new_image = ProjectImage(
                    project_id=project.id, 
                    image_path=filename,
                    caption=project.title
                )
                db.session.add(new_image)
        
        db.session.commit()
        flash(f'El proyecto "{project.title}" ha sido actualizado.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al editar: {str(e)}', 'danger')
        print(e)

    return redirect(url_for('auth.dashboard'))