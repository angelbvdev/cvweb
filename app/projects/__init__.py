from flask import Blueprint

# 1. Definimos el objeto Blueprint (lo llamamos 'bp')
bp = Blueprint('projects', __name__)

# 2. IMPORTAMOS RUTAS AL FINAL
from . import routes