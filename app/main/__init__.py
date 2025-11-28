from flask import Blueprint

# 1. Definimos el objeto Blueprint (lo llamamos 'bp')
bp = Blueprint('main', __name__)

# 2. IMPORTAMOS RUTAS AL FINAL
# Esto evita el error de importación circular al ejecutar run.py
from . import routes