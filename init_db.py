"""
Script para inicializar o banco de dados.
Execute: python init_db.py
"""
from src.sql.database import init_db

if __name__ == '__main__':
    print("Iniciando criação do banco de dados...")
    db_manager = init_db()
    print("\n✓ Banco de dados inicializado com sucesso!")
    print(f"  Localização: {db_manager.database_url}")
    print("\nTabelas criadas:")
    print("  - usuarios")
    print("  - pontos_usuarios")
