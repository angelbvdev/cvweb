import click

from app import create_app
from app.extensions import db
from app.models import User
from flask_migrate import init as migrate_init, migrate as migrate_run, upgrade as migrate_upgrade, downgrade as migrate_downgrade

# CLI para tareas de administración
@click.group()
def cli():
    pass


@cli.command("create_db")
def create_db_command():
    """Crea todas las tablas configuradas en SQLAlchemy."""
    app = create_app()
    with app.app_context():
        db.create_all()
        click.echo("Tablas creadas correctamente.")


@cli.command("db_init")
@click.option("--directory", default="migrations", show_default=True, help="Directorio para los archivos de migración.")
def db_init_command(directory):
    """Inicializa el entorno de migraciones (equivale a flask db init)."""
    app = create_app()
    with app.app_context():
        migrate_init(directory=directory)
        click.echo(f"Entorno de migraciones inicializado en '{directory}'.")


@cli.command("db_migrate")
@click.option("-m", "--message", default="auto", show_default=True, help="Mensaje de la migración.")
@click.option("--directory", default="migrations", show_default=True, help="Directorio de migraciones.")
def db_migrate_command(message, directory):
    """Genera una nueva migración a partir de los modelos (equivale a flask db migrate)."""
    app = create_app()
    with app.app_context():
        migrate_run(message=message, directory=directory)
        click.echo(f"Migración generada en '{directory}' con mensaje: {message}")


@cli.command("db_upgrade")
@click.option("--directory", default="migrations", show_default=True, help="Directorio de migraciones.")
def db_upgrade_command(directory):
    """Aplica migraciones pendientes (equivale a flask db upgrade)."""
    app = create_app()
    with app.app_context():
        migrate_upgrade(directory=directory)
        click.echo("Migraciones aplicadas.")


@cli.command("db_downgrade")
@click.option("--step", default="-1", show_default=True, help="Pasos a deshacer. Usa -1 para deshacer la última.")
@click.option("--directory", default="migrations", show_default=True, help="Directorio de migraciones.")
def db_downgrade_command(step, directory):
    """Revierte migraciones (equivale a flask db downgrade)."""
    app = create_app()
    with app.app_context():
        migrate_downgrade(revision=step, directory=directory)
        click.echo(f"Reversión aplicada ({step}).")


@cli.command("create_admin")
@click.option("--username", prompt=True, help="Nombre de usuario del administrador.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Contraseña del administrador.",
)
def create_admin_command(username, password):
    """Crea o actualiza el usuario administrador."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(password)
            action = "actualizado"
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            action = "creado"

        db.session.commit()
        click.echo(f"Usuario admin {action}: {username}")


if __name__ == "__main__":
    cli()
