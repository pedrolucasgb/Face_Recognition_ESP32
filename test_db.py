"""
Script de teste rápido para validar a instalação do banco de dados.
"""
from src.sql.database import db_manager, init_db
from src.models import Usuario, PontoUsuario, TipoPonto, Base

def test_database_setup():
    """Testa se o banco foi criado corretamente."""
    print("🔍 Testando configuração do banco de dados...\n")
    
    # 1. Verificar conexão
    try:
        engine = db_manager.engine
        print(f"✓ Conexão estabelecida: {db_manager.database_url}")
    except Exception as e:
        print(f"✗ Erro na conexão: {e}")
        return False
    
    # 2. Verificar tabelas
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['usuarios', 'pontos_usuarios']
        print(f"\n📋 Tabelas encontradas: {tables}")
        
        for table in expected_tables:
            if table in tables:
                print(f"   ✓ {table}")
            else:
                print(f"   ✗ {table} - NÃO ENCONTRADA")
                return False
                
    except Exception as e:
        print(f"✗ Erro ao verificar tabelas: {e}")
        return False
    
    # 3. Testar inserção e consulta
    try:
        with db_manager.get_session() as session:
            # Criar usuário de teste
            test_user = Usuario(
                nome="Teste Sistema",
                matricula="TEST001",
                email="teste@sistema.com",
                ativo=True
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            
            print(f"\n✓ Usuário de teste criado: ID {test_user.id}")
            
            # Criar ponto de teste
            test_ponto = PontoUsuario(
                usuario_id=test_user.id,
                tipo=TipoPonto.ENTRADA,
                confianca=0.95
            )
            session.add(test_ponto)
            session.commit()
            
            print(f"✓ Ponto de teste criado: ID {test_ponto.id}")
            
            # Consultar
            usuario = session.query(Usuario).filter(Usuario.matricula == "TEST001").first()
            if usuario:
                print(f"✓ Consulta bem-sucedida: {usuario.nome}")
            
            # Limpar testes
            session.delete(test_ponto)
            session.delete(test_user)
            session.commit()
            print("✓ Dados de teste removidos")
            
    except Exception as e:
        print(f"✗ Erro nos testes de CRUD: {e}")
        return False
    
    print("\n" + "="*50)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*50)
    print("\nO banco de dados está pronto para uso.")
    print("Execute 'python exemplo_uso_db.py' para ver exemplos práticos.\n")
    
    return True


if __name__ == '__main__':
    print("="*50)
    print("TESTE DE CONFIGURAÇÃO DO BANCO DE DADOS")
    print("="*50 + "\n")
    
    # Inicializar banco se necessário
    try:
        init_db()
    except:
        pass  # Já existe
    
    # Executar testes
    test_database_setup()
