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

Para inicializar la base de datos dentro del contenedor:
```
docker compose exec cvweb python -c "from app import create_app; from app.extensions import db; app = create_app(); with app.app_context(): db.create_all()"
```
