from datetime import datetime, timezone

from flask import render_template, abort, request, Response, url_for
from sqlalchemy.exc import OperationalError
from sqlalchemy import desc, or_, func, case
from sqlalchemy import inspect
from sqlalchemy.orm import load_only
from flask_login import current_user
from app.extensions import db
from app.models import BlogPost, BlogTag, post_tags
from . import bp


_POSTS = [
    {
        "slug": "welcome",
        "title": "Welcome",
        "excerpt": "Notes on building reliable data pipelines, backend services, and shipping to production.",
        "content": (
            "This is the new blog space for the portfolio.\n\n"
            "Next steps:\n"
            "- Add a database-backed post model\n"
            "- Create an admin editor\n"
            "- Support Markdown rendering\n"
        ),
        "published": True,
    }
]

def _reading_minutes_from_content(content: str) -> int:
    words = len((content or "").split())
    return max(1, (words + 219) // 220)


def _annotate_post(post):
    content = post.content if hasattr(post, "content") else post.get("content", "")
    reading_minutes = _reading_minutes_from_content(content or "")
    if hasattr(post, "__dict__"):
        post.reading_minutes = reading_minutes
        post.display_date = (getattr(post, "published_at", None) or getattr(post, "created_at", None))
    else:
        post["reading_minutes"] = reading_minutes
        post["display_date"] = None
    return post


def _paginate(query, page: int, per_page: int):
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 24:
        per_page = 24
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, total, pages, page, per_page


def _blog_posts_has_meta_columns() -> bool:
    try:
        cols = {c["name"] for c in inspect(BlogPost.query.session.bind).get_columns("blog_posts")}
        return "meta_description" in cols and "meta_title" in cols
    except Exception:
        return False


@bp.route("/")
def index():
    try:
        q = (request.args.get("q") or "").strip()
        tag = (request.args.get("tag") or "").strip()
        page = int(request.args.get("page") or 1)
        per_page = int(request.args.get("per_page") or 9)

        query = BlogPost.query.options(
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
        if not current_user.is_authenticated:
            query = query.filter_by(is_published=True)

        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    BlogPost.title.ilike(like),
                    BlogPost.slug.ilike(like),
                    BlogPost.excerpt.ilike(like),
                    BlogPost.content.ilike(like),
                )
            )

        if tag:
            query = query.join(BlogPost.tags).filter(BlogTag.slug == tag)

        query = query.order_by(desc(BlogPost.published_at), desc(BlogPost.created_at))
        posts, total, pages, page, per_page = _paginate(query, page, per_page)
    except OperationalError:
        posts = [p for p in _POSTS if p.get("published")]
        total = len(posts)
        pages = 1
        page = 1
        per_page = len(posts) or 1
        q = ""
        tag = ""

    posts = [_annotate_post(p) for p in posts]

    try:
        count_expr = func.count(BlogPost.id)
        if not current_user.is_authenticated:
            count_expr = func.sum(case((BlogPost.is_published.is_(True), 1), else_=0))

        tag_rows = (
            db.session.query(BlogTag, count_expr)
            .outerjoin(post_tags, BlogTag.id == post_tags.c.tag_id)
            .outerjoin(BlogPost, BlogPost.id == post_tags.c.post_id)
            .group_by(BlogTag.id)
            .order_by(BlogTag.name.asc())
            .all()
        )
        tags = [t for t, _ in tag_rows]
        tag_counts = {t.slug: int(c or 0) for t, c in tag_rows}
    except Exception:
        tags = []
        tag_counts = {}

    return render_template(
        "blog/index.html",
        title="Blog",
        posts=posts,
        q=q,
        selected_tag=tag,
        tags=tags,
        tag_counts=tag_counts,
        total=total,
        pages=pages,
        page=page,
        per_page=per_page,
        meta_description="Posts on data engineering, backend development, and DevOps.",
    )


@bp.route("/<slug>")
def post_detail(slug: str):
    try:
        query = (
            BlogPost.query.options(
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
            .filter_by(slug=slug)
        )
        if not current_user.is_authenticated:
            query = query.filter_by(is_published=True)
        post = query.first()
    except OperationalError:
        post = next((p for p in _POSTS if p.get("published") and p.get("slug") == slug), None)
    if not post:
        abort(404)
    title = post.title if hasattr(post, "title") else post["title"]
    post = _annotate_post(post)
    has_meta = _blog_posts_has_meta_columns()
    meta_description = (getattr(post, "meta_description") if has_meta else None) or getattr(post, "excerpt", None) or ""
    return render_template("blog/post_detail.html", title=title, post=post, meta_description=meta_description)


@bp.route("/rss.xml")
def rss():
    try:
        posts = (
            BlogPost.query.filter_by(is_published=True)
            .order_by(desc(BlogPost.published_at), desc(BlogPost.created_at))
            .limit(20)
            .all()
        )
    except OperationalError:
        posts = [p for p in _POSTS if p.get("published")][:20]

    items = []
    for p in posts:
        title = p.title if hasattr(p, "title") else p.get("title", "Post")
        slug = p.slug if hasattr(p, "slug") else p.get("slug", "")
        link = url_for("blog.post_detail", slug=slug, _external=True)
        excerpt = p.excerpt if hasattr(p, "excerpt") else p.get("excerpt", "")
        dt = getattr(p, "published_at", None) or getattr(p, "created_at", None) or datetime.now(timezone.utc)
        if isinstance(dt, datetime) and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
        items.append(
            f"""
    <item>
      <title><![CDATA[{title}]]></title>
      <link>{link}</link>
      <guid>{link}</guid>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[{excerpt or ''}]]></description>
    </item>"""
        )

    channel_link = url_for("blog.index", _external=True)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Angel Burgos - Blog</title>
    <link>{channel_link}</link>
    <description>Posts on data engineering, backend development, and DevOps.</description>
{''.join(items)}
  </channel>
</rss>
"""
    return Response(xml, mimetype="application/rss+xml; charset=utf-8")
