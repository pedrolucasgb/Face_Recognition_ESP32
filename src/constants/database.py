import os
from dotenv import load_dotenv

load_dotenv()

# Configuração do banco de dados
host = os.getenv('DB_HOST')
port = os.getenv('DB_PORT')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME')

DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"