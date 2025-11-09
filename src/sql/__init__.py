"""
Módulo SQL - Configuração e gerenciamento de banco de dados.
"""
from .database import db_manager, init_db, DatabaseManager

__all__ = ['db_manager', 'init_db', 'DatabaseManager']
