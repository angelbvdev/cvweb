from flask import Blueprint, render_template
from app.models import Project as Proyecto #Alias en español porque si no me lío jaja
from app.extensions import db

# --- Blueprint ---
bp = Blueprint('projects', __name__, template_folder='templates')


@bp.route('/')
def projects_home():
    """Listado de proyectos obtenidos de la base de datos"""
    
    # Consulta a la Base de Datos 
    # Esto carga TODOS los objetos 'Proyecto' de tu tabla.
    proyectos = Proyecto.query.all() 
    
    return render_template(
        'projects.html', 
        title='Projects',
        proyectos=proyectos
    )

@bp.route('/<int:project_id>')
def project_detail(project_id):
    """Detalle de un proyecto obtenido de la base de datos"""
    
    #Consulta a la Base de Datos 
    # Busca el proyecto por su ID. Si no lo encuentra, lanza un error 404.
    proyecto = Proyecto.query.get_or_404(project_id)
    
    return render_template(
        'project_detail.html', 
        title=proyecto.title, # Nota: Accedemos a los atributos como objetos, no diccionarios
        proyecto=proyecto
    )
