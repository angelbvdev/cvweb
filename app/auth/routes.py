from datetime import datetime
import os
from uuid import uuid4

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Project, ProjectImage, BlogPost
from . import bp
from werkzeug.utils import secure_filename


def _is_allowed_image(filename: str) -> bool:
    ext = (filename.rsplit('.', 1)[-1] if '.' in filename else '').lower()
    return ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def _blog_upload_dir() -> str:
    base = current_app.config['UPLOAD_FOLDER']
    return os.path.join(base, 'blog')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('auth.dashboard')
        return redirect(next_page)
        
    return render_template('auth/login.html', title='Sign in')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    # Obtenemos los proyectos ordenados por fecha (más reciente primero)
    projects = Project.query.order_by(Project.created_at.desc()).all()
    stats = {
        'total': len(projects),
        'with_github': sum(1 for p in projects if p.github_url),
        'with_demo': sum(1 for p in projects if p.website_url),
        'with_images': sum(1 for p in projects if p.images),
    }
    category_counts = {}
    for p in projects:
        key = p.category_slug or 'uncategorized'
        category_counts[key] = category_counts.get(key, 0) + 1

    return render_template(
        'auth/dashboard.html',
        title='Dashboard',
        projects=projects,
        stats=stats,
        category_counts=category_counts
    )


@bp.route('/blog')
@login_required
def blog():
    try:
        posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    except Exception as e:
        posts = []
        flash(f'Blog tables not ready yet ({e}). Run migrations to enable blog admin.', 'warning')
    return render_template('auth/blog.html', title='Blog', posts=posts)


@bp.route('/blog/create', methods=['POST'])
@login_required
def create_blog_post():
    title = (request.form.get('title') or '').strip()
    slug = (request.form.get('slug') or '').strip()
    excerpt = (request.form.get('excerpt') or '').strip() or None
    content = (request.form.get('content') or '').strip()
    is_published = request.form.get('is_published') == 'on'

    if not title or not slug or not content:
        flash('Title, slug, and content are required.', 'danger')
        return redirect(url_for('auth.blog'))

    post = BlogPost(
        title=title,
        slug=slug,
        excerpt=excerpt,
        content=content,
        is_published=is_published,
        published_at=datetime.utcnow() if is_published else None,
    )

    cover = request.files.get('cover_image')
    if cover and cover.filename:
        if not _is_allowed_image(cover.filename):
            flash('Cover image must be PNG/JPG/JPEG/WEBP/GIF.', 'danger')
            return redirect(url_for('auth.blog'))
        os.makedirs(_blog_upload_dir(), exist_ok=True)
        safe_name = secure_filename(cover.filename)
        unique_name = f"{uuid4().hex}_{safe_name}"
        cover.save(os.path.join(_blog_upload_dir(), unique_name))
        post.cover_image_path = unique_name

    try:
        db.session.add(post)
        db.session.commit()
        flash('Post created.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating post: {str(e)}', 'danger')

    return redirect(url_for('auth.blog'))


@bp.route('/blog/edit/<int:id>', methods=['POST'])
@login_required
def edit_blog_post(id):
    post = BlogPost.query.get_or_404(id)

    title = (request.form.get('title') or '').strip()
    slug = (request.form.get('slug') or '').strip()
    excerpt = (request.form.get('excerpt') or '').strip() or None
    content = (request.form.get('content') or '').strip()
    is_published = request.form.get('is_published') == 'on'

    if not title or not slug or not content:
        flash('Title, slug, and content are required.', 'danger')
        return redirect(url_for('auth.blog'))

    post.title = title
    post.slug = slug
    post.excerpt = excerpt
    post.content = content
    post.is_published = is_published
    if is_published and not post.published_at:
        post.published_at = datetime.utcnow()
    if not is_published:
        post.published_at = None

    cover = request.files.get('cover_image')
    if cover and cover.filename:
        if not _is_allowed_image(cover.filename):
            flash('Cover image must be PNG/JPG/JPEG/WEBP/GIF.', 'danger')
            return redirect(url_for('auth.blog'))
        os.makedirs(_blog_upload_dir(), exist_ok=True)
        safe_name = secure_filename(cover.filename)
        unique_name = f"{uuid4().hex}_{safe_name}"
        cover.save(os.path.join(_blog_upload_dir(), unique_name))

        if post.cover_image_path:
            old_path = os.path.join(_blog_upload_dir(), post.cover_image_path)
            if os.path.exists(old_path):
                os.remove(old_path)

        post.cover_image_path = unique_name

    try:
        db.session.commit()
        flash('Post updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating post: {str(e)}', 'danger')

    return redirect(url_for('auth.blog'))


@bp.route('/blog/delete/<int:id>', methods=['POST'])
@login_required
def delete_blog_post(id):
    post = BlogPost.query.get_or_404(id)
    try:
        if post.cover_image_path:
            path = os.path.join(_blog_upload_dir(), post.cover_image_path)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting post: {str(e)}', 'danger')
    return redirect(url_for('auth.blog'))

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
        
        flash('Project and images created successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating project: {str(e)}', 'danger')
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
        
        flash(f'The project "{project.title}" and its images have been deleted.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting: {str(e)}', 'danger')
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
        flash(f'The project "{project.title}" has been updated.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error editing: {str(e)}', 'danger')
        print(e)

    return redirect(url_for('auth.dashboard'))
