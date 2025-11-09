"""
Cliente ESP32-CAM para captura de stream MJPEG em thread separada
"""
import threading
import time
import cv2
import numpy as np
import requests
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ESP32CamClient:
    """Cliente para capturar frames de ESP32-CAM via stream MJPEG"""
    
    def __init__(self, stream_url: str, on_frame: Optional[Callable] = None):
        self.stream_url = stream_url
        self.on_frame = on_frame
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_frame: Optional[np.ndarray] = None
        self.last_error: Optional[str] = None
        self.lock = threading.Lock()
        
    def start(self):
        """Inicia a captura de frames em thread separada"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"ESP32-CAM client iniciado: {self.stream_url}")
    
    def stop(self):
        """Para a captura de frames"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("ESP32-CAM client parado")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Retorna cópia do último frame capturado"""
        with self.lock:
            return self.last_frame.copy() if self.last_frame is not None else None
    
    def _capture_loop(self):
        """Loop principal de captura de frames"""
        while self.running:
            try:
                # Conecta ao stream MJPEG
                response = requests.get(self.stream_url, stream=True, timeout=5)
                if response.status_code != 200:
                    raise Exception(f"Status code {response.status_code}")
                
                bytes_data = bytes()
                for chunk in response.iter_content(chunk_size=1024):
                    if not self.running:
                        break
                    
                    bytes_data += chunk
                    # Procura por marcadores JPEG
                    a = bytes_data.find(b'\xff\xd8')  # Início JPEG
                    b = bytes_data.find(b'\xff\xd9')  # Fim JPEG
                    
                    if a != -1 and b != -1:
                        jpg = bytes_data[a:b+2]
                        bytes_data = bytes_data[b+2:]
                        
                        # Decodifica JPEG para numpy array
                        frame = cv2.imdecode(
                            np.frombuffer(jpg, dtype=np.uint8),
                            cv2.IMREAD_COLOR
                        )
                        
                        if frame is not None:
                            with self.lock:
                                self.last_frame = frame
                                self.last_error = None
                            
                            # Callback se definido
                            if self.on_frame:
                                try:
                                    self.on_frame(frame)
                                except Exception as e:
                                    logger.error(f"Erro no callback: {e}")
            
            except Exception as e:
                error_msg = f"Erro ao capturar do ESP32-CAM: {e}"
                logger.warning(error_msg)
                with self.lock:
                    self.last_error = str(e)
                # Aguarda antes de tentar reconectar
                time.sleep(5)


# Instância global (se habilitado)
_esp32_client: Optional[ESP32CamClient] = None

def get_esp32_client(stream_url: str = None, on_frame: Callable = None) -> Optional[ESP32CamClient]:
    """Retorna a instância singleton do cliente ESP32"""
    global _esp32_client
    if _esp32_client is None and stream_url:
        _esp32_client = ESP32CamClient(stream_url, on_frame)
    return _esp32_client
