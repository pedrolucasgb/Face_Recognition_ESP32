"""
Configuração e conexão com o banco de dados.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from constants.database import DATABASE_URL


# Configuração do banco de dados
# Para desenvolvimento: SQLite
# Para produção: MySQL (descomentar e configurar)


# Criar engine
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False},
        echo=False  # Mude para True para debug SQL
    )
else:
    # Configuração para MySQL/PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )

# Session factory
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)


def init_db():
    """Inicializa o banco de dados criando todas as tabelas."""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    print("✓ Banco de dados inicializado com sucesso!")


def drop_db():
    """Remove todas as tabelas do banco de dados."""
    from .models import Base
    Base.metadata.drop_all(bind=engine)
    print("✓ Tabelas removidas com sucesso!")


@contextmanager
def get_db():
    """
    Context manager para obter uma sessão do banco de dados.
    
    Uso:
        with get_db() as db:
            usuarios = db.query(Usuario).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_db_session():
    """
    Generator para uso com dependências do Flask/FastAPI.
    
    Uso (Flask):
        @app.route('/users')
        def get_users():
            db = next(get_db_session())
            users = db.query(Usuario).all()
            return jsonify([u.to_dict() for u in users])
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
