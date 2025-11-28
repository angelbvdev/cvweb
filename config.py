import os
from dotenv import load_dotenv

# Cargar variables del archivo .env automáticamente
load_dotenv()

# Obtener la ruta base del proyecto 
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Configuración base de la aplicación."""
    # 1. Configuración General
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # 2. Configuración de la Base de Datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'cvweb.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 3. Configuración de Correo Electrónico
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # 4. Otros Parámetros
    ADMINS = ['angelbv.dev@gmail.com']