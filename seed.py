from datetime import datetime
from app import create_app
from app.models import db, Project, ProjectImage, ProjectCode

# --- DATOS DE PRUEBA (Asegúrate de que las CLAVES coincidan con models.py) ---
PROJECTS_DATA = [
    {
        'title': 'API RESTful de Inventario',
        'slug': 'api-inventario',
        'description': 'Construcción de una API RESTful para la gestión de inventario en una cadena de tiendas.',
        'long_description': 'Implementación de endpoints CRUD completos y autenticación basada en tokens.',
        'technologies': 'Python, Flask, SQLAlchemy, PostgreSQL',
        'github_url': 'https://github.com/angel/api-inventory',
        'website_url': None,
        'created_at': datetime.now(),
        # 🚨 ¡LA CORRECCIÓN AQUÍ! 🚨
        'category_slug': 'backend', 
        'images': [
            {'image_path': 'inventory_api/diagram.png', 'caption': 'Diagrama de la arquitectura'},
        ],
        # ...
    },
    {
        'title': 'Portafolio Web Personal',
        'slug': 'portfolio-web',
        'description': 'Mi sitio web profesional para mostrar proyectos, habilidades y experiencia.',
        'long_description': 'Diseño responsive implementado con Bootstrap y lógica de enrutamiento con Blueprints.',
        'technologies': 'Flask, Jinja2, Bootstrap, JavaScript',
        'github_url': 'https://github.com/angel/my-portfolio',
        'website_url': 'https://angel.dev',
        'created_at': datetime.now(),
        # 🚨 ¡LA CORRECCIÓN AQUÍ! 🚨
        'category_slug': 'frontend',
        'images': [
            {'image_path': 'portfolio/home.jpg', 'caption': 'Vista de la página de inicio'},
        ],
        # ...
    }
]

def seed_db():
    # 1. Crear la aplicación y establecer el contexto
    app = create_app()
    with app.app_context():
        
        # 2. Limpiar y recrear tablas
        # ¡ADVERTENCIA! Esto borrará TODOS los datos en las tablas: projects, project_images, project_code
        db.drop_all() 
        db.create_all()

        print("Base de datos limpia y tablas creadas (Project, ProjectImage, ProjectCode).")

        # 3. Insertar los datos de prueba
        for data in PROJECTS_DATA:
            # Separar datos de relaciones (images y code) de los datos principales
            images_data = data.pop('images', [])
            code_data = data.pop('code', [])
            
            # Crea la instancia principal del Projecto
            project = Project(**data) 
            db.session.add(project)

            # Insertar imágenes relacionadas
            for img_data in images_data:
                image = ProjectImage(**img_data)
                project.images.append(image) # Asocia la imagen al proyecto
            
            # Insertar snippets de código relacionados
            for code_snippet_data in code_data:
                code_snippet = ProjectCode(**code_snippet_data)
                project.code.append(code_snippet) # Asocia el código al proyecto

        # 4. Guardar todos los cambios
        db.session.commit()
        
        print(f" Se agregaron {len(PROJECTS_DATA)} proyectos y sus relaciones.")


if __name__ == '__main__':
    seed_db()