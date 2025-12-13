# cvweb

Aplicación Flask para mostrar proyectos y CV.

## Ejecutar con Docker
- Copia `.env.example` a `.env` y ajusta `SECRET_KEY`, `DATABASE_URL` (por defecto usa SQLite en `/data/cvweb.db`) y las credenciales de correo si las necesitas.
- Construye la imagen: `docker compose build`
- Levanta el contenedor: `docker compose up -d`
- La app queda disponible en `http://localhost:5000`

Para usar PostgreSQL, coloca la URL en `DATABASE_URL` dentro de `.env` (se acepta tanto `postgres://` como `postgresql://`).

Volúmenes usados:
- `cvweb_data`: guarda la base de datos SQLite en `/data/cvweb.db`
- `cvweb_uploads`: guarda las subidas en `app/static/uploads`

## Comandos de utilidad
- Crear tablas de la base de datos (usa la `DATABASE_URL` configurada):
  - Local: `python manage.py create_db`
  - Docker: `docker compose exec cvweb python manage.py create_db`
- Crear o actualizar usuario admin:
  - Local: `python manage.py create_admin --username admin` (pedirá la contraseña)
  - Docker: `docker compose exec cvweb python manage.py create_admin --username admin`
- Migraciones (Flask-Migrate):
  - Inicializar entorno de migraciones: `python manage.py db_init`
  - Generar migración: `python manage.py db_migrate -m "mensaje"`
  - Aplicar migraciones: `python manage.py db_upgrade`
  - Revertir última migración: `python manage.py db_downgrade --step -1`
  - En Docker, anteponer `docker compose exec cvweb` a cualquiera de los comandos anteriores.
