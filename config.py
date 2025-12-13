import os
from dotenv import load_dotenv

# Cargar variables del archivo .env automáticamente
load_dotenv()

# Obtener la ruta base del proyecto 
basedir = os.path.abspath(os.path.dirname(__file__))

def _str_to_bool(value, default=False):
    if value is None:
        return default
    return str(value).lower() in {'1', 'true', 't', 'yes', 'y'}

class Config:
    """Configuración base de la aplicación."""
    # 1. Configuración General
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # 2. Configuración de la Base de Datos
    _database_url = os.environ.get('DATABASE_URL')
    if _database_url and _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _database_url or 'sqlite:///' + os.path.join(basedir, 'cvweb.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 3. Configuración de Correo Electrónico
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = _str_to_bool(os.environ.get('MAIL_USE_TLS'), True)
    MAIL_USE_SSL = _str_to_bool(os.environ.get('MAIL_USE_SSL'), False)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    
    # 4. Otros Parámetros
    ADMINS = ['angelbv.dev@gmail.com']

    # 5. Configuración de Subidas de Archivos
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB límite de subida

    # 6. Documentos (CV)
    DOCUMENTS_FOLDER = os.environ.get('DOCUMENTS_FOLDER') or os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/documents')
    CV_FILENAME = os.environ.get('CV_FILENAME') or 'cv_angel.pdf'
