"""
Configuração e gerenciamento do banco de dados.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import os

from models.models import Base


class DatabaseManager:
    """Gerenciador de conexão com o banco de dados."""
    
    def __init__(self, database_url=None):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            database_url: URL de conexão do banco de dados.
                         Se None, usa SQLite por padrão.
        """
        if database_url is None:
            # Caminho padrão para SQLite
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database.db')
            database_url = f'sqlite:///{os.path.abspath(db_path)}'
        
        self.database_url = database_url
        
        # Configurações específicas para SQLite
        if database_url.startswith('sqlite'):
            self.engine = create_engine(
                database_url,
                connect_args={'check_same_thread': False},
                echo=False  # Mude para True para debug SQL
            )
        else:
            # Configurações para MySQL/PostgreSQL
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        
        # Session factory
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )
    
    def create_tables(self):
        """Cria todas as tabelas no banco de dados."""
        Base.metadata.create_all(bind=self.engine)
        print("✓ Tabelas criadas com sucesso!")
    
    def drop_tables(self):
        """Remove todas as tabelas do banco de dados."""
        Base.metadata.drop_all(bind=self.engine)
        print("✓ Tabelas removidas com sucesso!")
    
    @contextmanager
    def get_session(self):
        """
        Context manager para obter uma sessão do banco de dados.
        
        Uso:
            with db_manager.get_session() as session:
                session.query(Usuario).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_db(self):
        """
        Generator para usar com Flask/FastAPI dependency injection.
        
        Uso (Flask):
            @app.route('/users')
            def get_users():
                db = next(db_manager.get_db())
                users = db.query(Usuario).all()
                return jsonify([u.to_dict() for u in users])
        """
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Instância global do gerenciador (para usar com SQLite)
db_manager = DatabaseManager()


# Função helper para inicializar o banco
def init_db(database_url=None):
    """
    Inicializa o banco de dados.
    
    Args:
        database_url: URL de conexão (opcional)
    """
    global db_manager
    if database_url:
        db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager
