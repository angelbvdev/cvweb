from flask import render_template, abort
from sqlalchemy.exc import OperationalError
from sqlalchemy import desc
from app.models import BlogPost
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


@bp.route("/")
def index():
    try:
        posts = (
            BlogPost.query.filter_by(is_published=True)
            .order_by(desc(BlogPost.published_at), desc(BlogPost.created_at))
            .all()
        )
    except OperationalError:
        posts = [p for p in _POSTS if p.get("published")]
    return render_template("blog/index.html", title="Blog", posts=posts)


@bp.route("/<slug>")
def post_detail(slug: str):
    try:
        post = BlogPost.query.filter_by(is_published=True, slug=slug).first()
    except OperationalError:
        post = next((p for p in _POSTS if p.get("published") and p.get("slug") == slug), None)
    if not post:
        abort(404)
    title = post.title if hasattr(post, "title") else post["title"]
    return render_template("blog/post_detail.html", title=title, post=post)
