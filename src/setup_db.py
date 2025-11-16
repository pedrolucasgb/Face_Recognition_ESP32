"""
Script de inicialização do banco de dados
Cria as tabelas necessárias para o sistema
"""
from models.db import init_db, drop_db, get_db
from models.models import Base, Usuario, PontoUsuario, UsuarioLogin, TipoUsuario

def criar_usuario_admin():
    """Cria usuário admin padrão se não existir"""
    try:
        with get_db() as db:
            # Verifica se admin já existe
            admin_existente = db.query(UsuarioLogin).filter(
                UsuarioLogin.username == 'admin'
            ).first()
            
            if not admin_existente:
                # Cria usuário admin
                admin = UsuarioLogin(
                    username='admin',
                    email='admin@sistema.com',
                    tipo=TipoUsuario.ADMIN,
                    ativo=True
                )
                admin.set_password('admin123')
                
                db.add(admin)
                db.commit()
                print("   ✓ Usuário admin criado com sucesso")
            else:
                print("   ✓ Usuário admin já existe")
                
    except Exception as e:
        print(f"   ❌ Erro ao criar usuário admin: {e}")

def main():
    print("=" * 60)
    print("INICIALIZAÇÃO DO BANCO DE DADOS")
    print("Sistema de Reconhecimento Facial")
    print("=" * 60)
    
    resposta = input("\nDeseja recriar o banco de dados? (S/N): ")
    
    if resposta.upper() == 'S':
        print("\n⚠️  Removendo tabelas existentes...")
        try:
            drop_db()
        except Exception as e:
            print(f"Aviso: {e}")
    
    print("\n✓ Criando tabelas...")
    init_db()
    
    print("\n✓ Criando usuário admin padrão...")
    criar_usuario_admin()
    
    print("\n" + "=" * 60)
    print("✓ BANCO DE DADOS INICIALIZADO COM SUCESSO!")
    print("=" * 60)
    print("\nTabelas criadas:")
    print("  - usuarios")
    print("  - pontos_usuarios")
    print("  - usuarios_login")
    print("\nUsuário admin criado:")
    print("  Username: admin")
    print("  Password: admin123")
    print("  Email: admin@sistema.com")
    print("\nVocê pode agora executar a aplicação com: python app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
