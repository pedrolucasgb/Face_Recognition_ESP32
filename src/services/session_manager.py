"""
Gerenciador de sessões de câmera de múltiplos clientes
"""
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import numpy as np

class CameraSession:
    """Representa uma sessão de câmera de um cliente"""
    def __init__(self, session_id: str, source_type: str = 'browser'):
        self.session_id = session_id
        self.source_type = source_type  # 'browser', 'esp32'
        self.last_frame: Optional[np.ndarray] = None
        self.last_update = datetime.utcnow()
        self.metadata = {}
        self.lock = threading.Lock()
        
    def update_frame(self, frame: np.ndarray, metadata: dict = None):
        """Atualiza o frame da sessão"""
        with self.lock:
            self.last_frame = frame
            self.last_update = datetime.utcnow()
            if metadata:
                self.metadata.update(metadata)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Retorna cópia do último frame"""
        with self.lock:
            return self.last_frame.copy() if self.last_frame is not None else None
    
    def is_active(self, timeout_seconds: int = 300) -> bool:
        """Verifica se a sessão ainda está ativa"""
        return (datetime.utcnow() - self.last_update).total_seconds() < timeout_seconds


class SessionManager:
    """Gerencia múltiplas sessões de câmera"""
    def __init__(self):
        self._sessions: Dict[str, CameraSession] = {}
        self._lock = threading.Lock()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def create_session(self, source_type: str = 'browser') -> str:
        """Cria uma nova sessão e retorna o ID"""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = CameraSession(session_id, source_type)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[CameraSession]:
        """Retorna uma sessão pelo ID"""
        with self._lock:
            return self._sessions.get(session_id)
    
    def update_frame(self, session_id: str, frame: np.ndarray, metadata: dict = None) -> bool:
        """Atualiza o frame de uma sessão"""
        session = self.get_session(session_id)
        if session:
            session.update_frame(frame, metadata)
            return True
        return False
    
    def get_frame(self, session_id: str) -> Optional[np.ndarray]:
        """Retorna o último frame de uma sessão"""
        session = self.get_session(session_id)
        return session.get_frame() if session else None
    
    def list_active_sessions(self, timeout_seconds: int = 300) -> list:
        """Lista todas as sessões ativas"""
        with self._lock:
            return [
                {
                    'session_id': sid,
                    'source_type': session.source_type,
                    'last_update': session.last_update.isoformat(),
                    'has_frame': session.last_frame is not None
                }
                for sid, session in self._sessions.items()
                if session.is_active(timeout_seconds)
            ]
    
    def remove_session(self, session_id: str):
        """Remove uma sessão"""
        with self._lock:
            self._sessions.pop(session_id, None)
    
    def _cleanup_loop(self):
        """Loop de limpeza de sessões inativas"""
        while True:
            time.sleep(60)  # Verifica a cada minuto
            with self._lock:
                inactive = [
                    sid for sid, session in self._sessions.items()
                    if not session.is_active(300)
                ]
                for sid in inactive:
                    del self._sessions[sid]


# Instância global
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """Retorna a instância singleton do gerenciador de sessões"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
