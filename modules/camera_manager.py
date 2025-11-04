import cv2
import time
from datetime import datetime


class CameraManager:
    """Classe responsável pelo gerenciamento da câmera"""
    
    def __init__(self, device_index=0):
        self.device_index = device_index
        self.camera = None
        self.is_running = False
        self.current_frame = None
        self.setup_camera()
    
    def setup_camera(self):
        """Inicializa a câmera"""
        self.camera = cv2.VideoCapture(self.device_index)
        
        if not self.camera.isOpened():
            raise RuntimeError(f"Erro: não foi possível abrir a webcam {self.device_index}.")
        
        # Configurações da câmera para melhor performance
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"Câmera {self.device_index} inicializada com sucesso!")
    
    def read_frame(self):
        """Lê um frame da câmera"""
        if not self.camera or not self.camera.isOpened():
            return False, None
        
        success, frame = self.camera.read()
        
        if success:
            self.current_frame = frame
        
        return success, frame
    
    def get_current_frame(self):
        """Retorna o frame atual"""
        return self.current_frame
    
    def release(self):
        """Libera a câmera"""
        if self.camera and self.camera.isOpened():
            self.camera.release()
            print("Câmera liberada.")
    
    def restart_camera(self):
        """Reinicia a câmera"""
        self.release()
        time.sleep(1)
        self.setup_camera()
    
    def is_camera_available(self):
        """Verifica se a câmera está disponível"""
        return self.camera is not None and self.camera.isOpened()


class FrameProcessor:
    """Classe responsável pelo processamento de frames"""
    
    def __init__(self):
        pass
    
    def add_timestamp(self, frame):
        """Adiciona timestamp ao frame"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
                   cv2.LINE_AA)
        return frame
    
    def draw_face_box(self, frame, face_coords, label="", color=(0, 255, 0), thickness=2):
        """Desenha caixa ao redor do rosto"""
        x, y, w, h = face_coords
        
        # Desenha retângulo
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        
        if label:
            # Calcula tamanho do texto
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            font_thickness = 2
            
            (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, font_thickness)
            
            # Desenha fundo do texto
            cv2.rectangle(frame, (x, y - text_height - 10), 
                         (x + text_width + 10, y), color, -1)
            
            # Desenha texto
            cv2.putText(frame, label, (x + 5, y - 5),
                       font, font_scale, (0, 0, 0), font_thickness, cv2.LINE_AA)
        
        return frame
    
    def draw_recognition_progress(self, frame, progress, name, position=(10, 70)):
        """Desenha barra de progresso do reconhecimento"""
        x, y = position
        bar_width = 200
        bar_height = 20
        
        # Fundo da barra
        cv2.rectangle(frame, (x, y), (x + bar_width, y + bar_height), (50, 50, 50), -1)
        
        # Progresso
        progress_width = int(bar_width * progress)
        color = (0, 255, 0) if progress >= 1.0 else (0, 165, 255)  # Verde se completo, laranja se em progresso
        cv2.rectangle(frame, (x, y), (x + progress_width, y + bar_height), color, -1)
        
        # Borda
        cv2.rectangle(frame, (x, y), (x + bar_width, y + bar_height), (255, 255, 255), 2)
        
        # Texto
        text = f"Reconhecendo: {name} ({progress*100:.0f}%)"
        cv2.putText(frame, text, (x, y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        
        return frame
    
    def draw_info_panel(self, frame, info_text, position=(10, 100)):
        """Desenha painel de informações"""
        x, y = position
        
        # Divide o texto em linhas
        lines = info_text.split('\n')
        line_height = 25
        
        for i, line in enumerate(lines):
            if line.strip():  # Ignora linhas vazias
                cv2.putText(frame, line, (x, y + i * line_height),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        
        return frame
    
    def encode_frame_for_web(self, frame):
        """Codifica frame para streaming web"""
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        if ret:
            return buffer.tobytes()
        
        return None
    
    def create_web_stream_frame(self, frame_bytes):
        """Cria frame formatado para streaming web"""
        return (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')