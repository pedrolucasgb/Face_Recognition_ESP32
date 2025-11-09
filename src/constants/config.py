"""
Configurações do sistema de reconhecimento facial
"""
import os
from typing import Optional

# Configuração do ESP32-CAM
ESP32_CAM_ENABLED = os.getenv('ESP32_CAM_ENABLED', 'false').lower() == 'true'
ESP32_CAM_URL = os.getenv('ESP32_CAM_URL', 'http://192.168.1.100:81/stream')
ESP32_SERVER_IP = os.getenv('ESP32_SERVER_IP', '192.168.1.10')  # IP específico onde ESP32 é ativado

# Configurações de sessão
SESSION_TIMEOUT_SECONDS = int(os.getenv('SESSION_TIMEOUT_SECONDS', '300'))  # 5 minutos
FRAME_UPLOAD_MAX_SIZE_MB = int(os.getenv('FRAME_UPLOAD_MAX_SIZE_MB', '5'))

# Configurações de camera
CAMERA_MODE = os.getenv('CAMERA_MODE', 'client')  # 'client', 'server', 'esp32', 'auto'
