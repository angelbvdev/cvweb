from app import create_app
from app.models import db  # Importar db desde models.py

app = create_app()

with app.app_context():
   
    db.init_app(app)     
  
    db.create_all()
    print("¡Base de datos creada!")
