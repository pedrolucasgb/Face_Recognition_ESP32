"""
Módulos do Sistema de Reconhecimento Facial
"""

from .face_recognition import FaceRecognizer, FaceDetector, FaceRegistration
from .ponto_manager import PontoManager
from .camera_manager import CameraManager, FrameProcessor

__all__ = [
    'FaceRecognizer',
    'FaceDetector', 
    'FaceRegistration',
    'PontoManager',
    'CameraManager',
    'FrameProcessor'
]