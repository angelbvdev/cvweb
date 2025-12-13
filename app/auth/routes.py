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


def _documents_dir() -> str:
    return current_app.config.get('DOCUMENTS_FOLDER') or os.path.join(current_app.root_path, 'static', 'documents')


def _cv_path() -> str:
    filename = current_app.config.get('CV_FILENAME') or 'cv_angel.pdf'
    return os.path.join(_documents_dir(), filename)


def _looks_like_pdf(file_storage) -> bool:
    try:
        head = file_storage.stream.read(1024) or b""
        file_storage.stream.seek(0)
        head = head.lstrip()
        return head.startswith(b"%PDF-")
    except Exception:
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass
        return False

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

    cv_filename = current_app.config.get('CV_FILENAME') or 'cv_angel.pdf'
    cv_path = _cv_path()
    cv_exists = os.path.exists(cv_path)
    cv_size = None
    cv_size_display = None
    if cv_exists:
        try:
            cv_size = os.path.getsize(cv_path)
            if cv_size < 1024:
                cv_size_display = f"{cv_size} B"
            elif cv_size < 1024 * 1024:
                cv_size_display = f"{round(cv_size / 1024)} KB"
            else:
                cv_size_display = f"{cv_size / (1024 * 1024):.1f} MB"
        except Exception:
            cv_size = None
            cv_size_display = None

    return render_template(
        'auth/dashboard.html',
        title='Dashboard',
        projects=projects,
        stats=stats,
        category_counts=category_counts,
        cv_filename=cv_filename,
        cv_exists=cv_exists,
        cv_size=cv_size,
        cv_size_display=cv_size_display,
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

    saved_cover_path = None
    cover = request.files.get('cover_image')
    if cover and cover.filename:
        if not _is_allowed_image(cover.filename):
            flash('Cover image must be PNG/JPG/JPEG/WEBP/GIF.', 'danger')
            return redirect(url_for('auth.blog'))
        os.makedirs(_blog_upload_dir(), exist_ok=True)
        safe_name = secure_filename(cover.filename)
        unique_name = f"{uuid4().hex}_{safe_name}"
        saved_cover_path = os.path.join(_blog_upload_dir(), unique_name)
        cover.save(saved_cover_path)
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
        if saved_cover_path and os.path.exists(saved_cover_path):
            try:
                os.remove(saved_cover_path)
            except Exception:
                pass
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
    remove_cover_image = request.form.get('remove_cover_image') == 'on'

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

    old_cover_path_to_delete = None
    new_cover_path_saved = None
    cover = request.files.get('cover_image')
    if cover and cover.filename:
        if not _is_allowed_image(cover.filename):
            flash('Cover image must be PNG/JPG/JPEG/WEBP/GIF.', 'danger')
            return redirect(url_for('auth.blog'))
        os.makedirs(_blog_upload_dir(), exist_ok=True)
        safe_name = secure_filename(cover.filename)
        unique_name = f"{uuid4().hex}_{safe_name}"
        new_cover_path_saved = os.path.join(_blog_upload_dir(), unique_name)
        cover.save(new_cover_path_saved)
        if post.cover_image_path:
            old_cover_path_to_delete = os.path.join(_blog_upload_dir(), post.cover_image_path)
        post.cover_image_path = unique_name
    elif remove_cover_image and post.cover_image_path:
        old_cover_path_to_delete = os.path.join(_blog_upload_dir(), post.cover_image_path)
        post.cover_image_path = None

    try:
        db.session.commit()
        if old_cover_path_to_delete and os.path.exists(old_cover_path_to_delete):
            try:
                os.remove(old_cover_path_to_delete)
            except Exception:
                pass
        flash('Post updated.', 'success')
    except Exception as e:
        db.session.rollback()
        if new_cover_path_saved and os.path.exists(new_cover_path_saved):
            try:
                os.remove(new_cover_path_saved)
            except Exception:
                pass
        flash(f'Error updating post: {str(e)}', 'danger')

    return redirect(url_for('auth.blog'))


@bp.route('/blog/delete/<int:id>', methods=['POST'])
@login_required
def delete_blog_post(id):
    post = _blog_post_query_safe().filter(BlogPost.id == id).first_or_404()
    try:
        cover_path = os.path.join(_blog_upload_dir(), post.cover_image_path) if post.cover_image_path else None
        db.session.delete(post)
        db.session.commit()
        if cover_path and os.path.exists(cover_path):
            try:
                os.remove(cover_path)
            except Exception:
                pass
        flash('Post deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting post: {str(e)}', 'danger')
    return redirect(url_for('auth.blog'))


@bp.route('/cv/upload', methods=['POST'])
@login_required
def upload_cv():
    cv_file = request.files.get('cv_file')
    if not cv_file or not cv_file.filename:
        flash('Choose a PDF file to upload.', 'danger')
        return redirect(url_for('auth.dashboard'))

    filename = (cv_file.filename or '').lower()
    if not filename.endswith('.pdf'):
        flash('CV must be a PDF file.', 'danger')
        return redirect(url_for('auth.dashboard'))
    if not _looks_like_pdf(cv_file):
        flash('That file does not look like a valid PDF.', 'danger')
        return redirect(url_for('auth.dashboard'))

    os.makedirs(_documents_dir(), exist_ok=True)
    target = _cv_path()
    tmp_name = f"{uuid4().hex}_{secure_filename(cv_file.filename)}"
    tmp_path = os.path.join(_documents_dir(), tmp_name)
    try:
        cv_file.save(tmp_path)
        os.replace(tmp_path, target)
        flash('CV uploaded successfully.', 'success')
    except Exception as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        flash(f'Error uploading CV: {str(e)}', 'danger')

    return redirect(url_for('auth.dashboard'))


@bp.route('/cv/delete', methods=['POST'])
@login_required
def delete_cv():
    path = _cv_path()
    try:
        if os.path.exists(path):
            os.remove(path)
            flash('CV deleted.', 'success')
        else:
            flash('No CV found to delete.', 'warning')
    except Exception as e:
        flash(f'Error deleting CV: {str(e)}', 'danger')
    return redirect(url_for('auth.dashboard'))

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

    saved_files = []
    try:
        custom_published_at = _parse_optional_publish_datetime(published_at_input)
        if published_at_input and not custom_published_at:
            flash('Published date must be in YYYY-MM-DD format.', 'danger')
            return redirect(url_for('auth.dashboard'))
        if custom_published_at:
            new_project.created_at = custom_published_at

        # 3. Guardamos el proyecto para generar el ID (sin commit aún)
        db.session.add(new_project)
        db.session.flush()

        # 4. Procesar las Imágenes
        # 'images' debe coincidir con el name="images" del input HTML
        files = request.files.getlist('images') 
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        for file in files:
            if file and file.filename != '':
                if not _is_allowed_image(file.filename):
                    try:
                        for path in saved_files:
                            if os.path.exists(path):
                                os.remove(path)
                    except Exception:
                        pass
                    db.session.rollback()
                    flash('Project images must be PNG/JPG/JPEG/WEBP/GIF.', 'danger')
                    return redirect(url_for('auth.dashboard'))
                # Limpiamos el nombre del archivo (seguridad)
                safe_name = secure_filename(file.filename)
                filename = f"{uuid4().hex}_{safe_name}"
                
                # Guardamos el archivo físico en la carpeta static/uploads
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                saved_files.append(file_path)
                
                # Guardamos la referencia en la Base de Datos
                # Aquí usamos new_project.id que acabamos de crear
                new_image = ProjectImage(
                    project_id=new_project.id, 
                    image_path=filename,
                    caption=title # Usamos el título como caption por defecto
                )
                db.session.add(new_image)
        
        db.session.commit()
        
        flash('Project and images created successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        try:
            for path in saved_files:
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass
        flash(f'Error creating project: {str(e)}', 'danger')
        print(e) # Para ver el error en consola si pasa algo

    return redirect(url_for('auth.dashboard'))


@bp.route('/delete_project/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    project = Project.query.get_or_404(id)
    
    try:
        image_paths = [
            os.path.join(current_app.config['UPLOAD_FOLDER'], img.image_path)
            for img in (project.images or [])
            if img.image_path
        ]

        # === Borrar de la Base de Datos ===
        # Gracias al cascade="all, delete" en tu modelo, esto borrará 
        # también las filas en la tabla ProjectImage automáticamente.
        db.session.delete(project)
        db.session.commit()

        for file_path in image_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        
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
    
    saved_files = []
    try:
        published_at_input = (request.form.get('published_at') or '').strip()
        custom_published_at = _parse_optional_publish_datetime(published_at_input)
        if published_at_input and not custom_published_at:
            flash('Published date must be in YYYY-MM-DD format.', 'danger')
            return redirect(url_for('auth.dashboard'))

        files = request.files.getlist('images')
        for file in files:
            if file and file.filename != '' and not _is_allowed_image(file.filename):
                flash('Project images must be PNG/JPG/JPEG/WEBP/GIF.', 'danger')
                return redirect(url_for('auth.dashboard'))

        delete_image_ids = request.form.getlist('delete_image_ids')
        delete_ids = set()
        for raw_id in delete_image_ids:
            try:
                delete_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue
        if delete_ids:
            images_to_delete = ProjectImage.query.filter(
                ProjectImage.project_id == project.id,
                ProjectImage.id.in_(delete_ids),
            ).all()
            delete_paths = []
            for img in images_to_delete:
                if img.image_path:
                    delete_paths.append(os.path.join(current_app.config['UPLOAD_FOLDER'], img.image_path))
                db.session.delete(img)
        else:
            delete_paths = []

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
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        for file in files:
            if file and file.filename != '':
                safe_name = secure_filename(file.filename)
                filename = f"{uuid4().hex}_{safe_name}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                saved_files.append(file_path)
                
                new_image = ProjectImage(
                    project_id=project.id, 
                    image_path=filename,
                    caption=project.title
                )
                db.session.add(new_image)
        
        db.session.commit()
        for file_path in delete_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        flash(f'The project "{project.title}" has been updated.', 'success')

    except Exception as e:
        db.session.rollback()
        try:
            for path in saved_files:
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass
        flash(f'Error editing: {str(e)}', 'danger')
        print(e)

    return redirect(url_for('auth.dashboard'))
