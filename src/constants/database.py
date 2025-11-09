import os
from dotenv import load_dotenv

load_dotenv()

# Configuração do banco de dados
# Para desenvolvimento: SQLite
# Para produção: MySQL/PostgreSQL

USE_SQLITE = os.getenv('USE_SQLITE', 'True').lower() == 'true'

if USE_SQLITE:
    # SQLite para desenvolvimento
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'face_recognition.db')
    DATABASE_URL = f"sqlite:///{DB_PATH}"
else:
    # MySQL para produção
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    database = os.getenv('DB_NAME')
    
    DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

print(f"Usando banco de dados: {DATABASE_URL}")