from datetime import datetime, date, timezone
import os
from uuid import uuid4

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import inspect
from sqlalchemy.orm import load_only
from app.extensions import db
from app.models import User, Project, ProjectImage, BlogPost, BlogTag
from . import bp
from werkzeug.utils import secure_filename


def _is_allowed_image(filename: str) -> bool:
    ext = (filename.rsplit('.', 1)[-1] if '.' in filename else '').lower()
    return ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def _blog_upload_dir() -> str:
    base = current_app.config['UPLOAD_FOLDER']
    return os.path.join(base, 'blog')

def _blog_posts_has_meta_columns() -> bool:
    try:
        cols = {c["name"] for c in inspect(db.engine).get_columns("blog_posts")}
        return "meta_description" in cols and "meta_title" in cols
    except Exception:
        return False


def _blog_post_query_safe():
    return BlogPost.query.options(
        load_only(
            BlogPost.id,
            BlogPost.slug,
            BlogPost.title,
            BlogPost.excerpt,
            BlogPost.content,
            BlogPost.cover_image_path,
            BlogPost.is_published,
            BlogPost.published_at,
            BlogPost.created_at,
            BlogPost.updated_at,
        )
    )


def _slugify_text(value: str, max_len: int = 120) -> str:
    value = (value or "").strip().lower()
    out = []
    prev_dash = False
    for ch in value:
        if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
            out.append(ch)
            prev_dash = False
            continue
        if ch in {" ", "-", "_", ".", "/"}:
            if not prev_dash and out:
                out.append("-")
                prev_dash = True
    slug = "".join(out).strip("-")[:max_len]
    return slug or "tag"


def _parse_tags(tag_string: str):
    raw = [t.strip() for t in (tag_string or "").split(",")]
    return [t for t in raw if t]


def _upsert_tags(tag_string: str):
    tags = []
    for name in _parse_tags(tag_string):
        slug = _slugify_text(name, max_len=80)
        tag = BlogTag.query.filter_by(slug=slug).first()
        if not tag:
            tag = BlogTag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)
    return tags


def _parse_optional_publish_datetime(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        if "T" in value:
            dt = datetime.fromisoformat(value)
        else:
            d = date.fromisoformat(value)
            dt = datetime(d.year, d.month, d.day)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _preserve_time_if_date_only(input_value: str, parsed_dt: datetime | None, existing_dt: datetime | None):
    if not parsed_dt or not existing_dt:
        return parsed_dt
    if "T" in (input_value or ""):
        return parsed_dt
    return parsed_dt.replace(
        hour=existing_dt.hour,
        minute=existing_dt.minute,
        second=existing_dt.second,
        microsecond=existing_dt.microsecond,
    )


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
        posts = _blog_post_query_safe().order_by(BlogPost.created_at.desc()).all()
    except Exception as e:
        posts = []
        flash(f'Blog tables not ready yet ({e}). Run migrations to enable blog admin.', 'warning')
    meta_ready = _blog_posts_has_meta_columns()
    if not meta_ready:
        flash('Blog admin needs a migration update. Run `flask db upgrade` to enable creating/editing posts.', 'warning')
    return render_template('auth/blog.html', title='Blog', posts=posts, blog_meta_ready=meta_ready)


@bp.route('/blog/create', methods=['POST'])
@login_required
def create_blog_post():
    if not _blog_posts_has_meta_columns():
        flash('Run `flask db upgrade` before creating posts (blog schema update pending).', 'danger')
        return redirect(url_for('auth.blog'))

    title = (request.form.get('title') or '').strip()
    slug = (request.form.get('slug') or '').strip()
    excerpt = (request.form.get('excerpt') or '').strip() or None
    content = (request.form.get('content') or '').strip()
    tags_string = (request.form.get('tags') or '').strip()
    meta_title = (request.form.get('meta_title') or '').strip() or None
    meta_description = (request.form.get('meta_description') or '').strip() or None
    is_published = request.form.get('is_published') == 'on'
    published_at_input = (request.form.get('published_at') or '').strip()

    if not title or not slug or not content:
        flash('Title, slug, and content are required.', 'danger')
        return redirect(url_for('auth.blog'))

    custom_published_at = _parse_optional_publish_datetime(published_at_input)
    if is_published and published_at_input and not custom_published_at:
        flash('Published date must be in YYYY-MM-DD format.', 'danger')
        return redirect(url_for('auth.blog'))

    post = BlogPost(
        title=title,
        slug=slug,
        excerpt=excerpt,
        content=content,
        meta_title=meta_title,
        meta_description=meta_description,
        is_published=is_published,
        published_at=(custom_published_at or datetime.utcnow()) if is_published else None,
    )
    post.tags = _upsert_tags(tags_string)

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
        if is_published:
            flash('Post created and published.', 'success')
        else:
            flash('Post created as a draft. Publish it to show on the public blog.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating post: {str(e)}', 'danger')

    return redirect(url_for('auth.blog'))


@bp.route('/blog/edit/<int:id>', methods=['POST'])
@login_required
def edit_blog_post(id):
    if not _blog_posts_has_meta_columns():
        flash('Run `flask db upgrade` before editing posts (blog schema update pending).', 'danger')
        return redirect(url_for('auth.blog'))

    post = _blog_post_query_safe().filter(BlogPost.id == id).first_or_404()

    title = (request.form.get('title') or '').strip()
    slug = (request.form.get('slug') or '').strip()
    excerpt = (request.form.get('excerpt') or '').strip() or None
    content = (request.form.get('content') or '').strip()
    tags_string = (request.form.get('tags') or '').strip()
    meta_title = (request.form.get('meta_title') or '').strip() or None
    meta_description = (request.form.get('meta_description') or '').strip() or None
    is_published = request.form.get('is_published') == 'on'
    published_at_input = (request.form.get('published_at') or '').strip()

    if not title or not slug or not content:
        flash('Title, slug, and content are required.', 'danger')
        return redirect(url_for('auth.blog'))

    custom_published_at = _parse_optional_publish_datetime(published_at_input)
    if is_published and published_at_input and not custom_published_at:
        flash('Published date must be in YYYY-MM-DD format.', 'danger')
        return redirect(url_for('auth.blog'))
    custom_published_at = _preserve_time_if_date_only(published_at_input, custom_published_at, post.published_at)

    post.title = title
    post.slug = slug
    post.excerpt = excerpt
    post.content = content
    post.meta_title = meta_title
    post.meta_description = meta_description
    post.tags = _upsert_tags(tags_string)
    post.is_published = is_published
    if is_published:
        if custom_published_at:
            post.published_at = custom_published_at
        elif not post.published_at:
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
    post = _blog_post_query_safe().filter(BlogPost.id == id).first_or_404()
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
    published_at_input = (request.form.get('published_at') or '').strip()

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
        custom_published_at = _parse_optional_publish_datetime(published_at_input)
        if published_at_input and not custom_published_at:
            flash('Published date must be in YYYY-MM-DD format.', 'danger')
            return redirect(url_for('auth.dashboard'))
        if custom_published_at:
            new_project.created_at = custom_published_at

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
        published_at_input = (request.form.get('published_at') or '').strip()
        custom_published_at = _parse_optional_publish_datetime(published_at_input)
        if published_at_input and not custom_published_at:
            flash('Published date must be in YYYY-MM-DD format.', 'danger')
            return redirect(url_for('auth.dashboard'))

        # 1. Actualizar datos de texto
        project.title = request.form.get('title')
        project.slug = request.form.get('slug')
        project.category_slug = request.form.get('category')
        project.technologies = request.form.get('technologies')
        project.description = request.form.get('description')
        project.long_description = request.form.get('long_description')
        project.github_url = request.form.get('github_url')
        project.website_url = request.form.get('website_url')
        if custom_published_at:
            project.created_at = _preserve_time_if_date_only(published_at_input, custom_published_at, project.created_at)

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
