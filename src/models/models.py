"""
Models do sistema de reconhecimento facial para controle de ponto.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship, declarative_base
import enum


Base = declarative_base()

class Usuario(Base):
    """
    Modelo de usuário do sistema.
    
    Attributes:
        id: Identificador único do usuário
        nome: Nome completo do usuário
        matricula: Matrícula/código de identificação único
        email: Email do usuário (opcional)
        face_encoding: Encoding facial serializado (JSON string)
        foto_path: Caminho para a foto de referência
        ativo: Flag indicando se o usuário está ativo no sistema
        criado_em: Data e hora de criação do registro
        atualizado_em: Data e hora da última atualização
    """
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False, index=True)
    cpf = Column(String(11), unique=True, nullable=False, index=True)
    matricula = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    foto_path = Column(String(500), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamento com pontos
    pontos = relationship("PontoUsuario", back_populates="usuario", cascade="all, delete-orphan")


class PontoUsuario(Base):
    """
    Modelo de registro de ponto dos usuários.
    
    Attributes:
        id: Identificador único do registro de ponto
        usuario_id: ID do usuário relacionado
        tipo: Tipo do ponto (entrada, saída, intervalo)
        data_hora: Data e hora do registro
        confianca: Nível de confiança do reconhecimento facial (0.0 a 1.0)
        foto_registro_path: Caminho para a foto capturada no momento do registro
        observacao: Observações adicionais sobre o registro
        localizacao: Localização GPS ou identificação do dispositivo (opcional)
        criado_em: Data e hora de criação do registro
    """
    __tablename__ = 'pontos_usuarios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, index=True)
    data_hora = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    confianca = Column(Float, nullable=True)  # Confiança do reconhecimento (0.0 a 1.0)
    foto_registro_path = Column(String(500), nullable=True)
    observacao = Column(String(500), nullable=True)
    dispositivo = Column(String(255), nullable=True)  # Ex: "ESP32" ou outro método de identificação
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamento com usuário
    usuario = relationship("Usuario", back_populates="pontos")
    
