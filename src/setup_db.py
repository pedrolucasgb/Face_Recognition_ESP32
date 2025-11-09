"""
Script de inicialização do banco de dados
Cria as tabelas necessárias para o sistema
"""
from models.db import init_db, drop_db
from models.models import Base, Usuario, PontoUsuario

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
    
    print("\n" + "=" * 60)
    print("✓ BANCO DE DADOS INICIALIZADO COM SUCESSO!")
    print("=" * 60)
    print("\nTabelas criadas:")
    print("  - usuarios")
    print("  - pontos_usuarios")
    print("\nVocê pode agora executar a aplicação com: python app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
