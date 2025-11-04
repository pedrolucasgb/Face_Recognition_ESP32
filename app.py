from flask import Flask, render_template, Response, jsonify, request
import cv2
import threading
import time
from datetime import datetime

# Importa os módulos criados
from modules import FaceRecognizer, PontoManager, CameraManager, FrameProcessor, FaceRegistration
import json
import os

app = Flask(__name__)

# ---------- Configurações ----------
DATA_DIR = "rostos"
DEVICE_INDEX = 0
MIN_FACE_SIZE = (80, 80)
CONFIDENCE_THRESHOLD = 70.0
PONTOS_FILE = "pontos_registrados.json"
# -----------------------------------

class FaceRecognitionSystem:
    def __init__(self):
        self.face_recognizer = FaceRecognizer(DATA_DIR, CONFIDENCE_THRESHOLD)
        self.ponto_manager = PontoManager(PONTOS_FILE)
        self.camera_manager = CameraManager(DEVICE_INDEX)
        self.frame_processor = FrameProcessor()
        self.last_recognition = {"nome": None, "horario": None}
        self.is_running = True
        
        print("Sistema de reconhecimento facial inicializado!")
    
    def process_recognition_with_timer(self, nome, confidence):
        """Processa reconhecimento com timer de 3 segundos"""
        registered, recognition_time = self.ponto_manager.start_recognition_session(nome)
        
        if registered:
            # Atualiza último reconhecimento
            now = datetime.now()
            horario = now.strftime("%Y-%m-%d %H:%M:%S")
            self.last_recognition = {"nome": nome, "horario": horario}
            
        return registered, recognition_time
    
    def generate_frames(self):
        """Gera frames com reconhecimento facial"""
        while self.is_running:
            success, frame = self.camera_manager.read_frame()
            if not success:
                time.sleep(0.1)
                continue
            
            # Adiciona timestamp
            frame = self.frame_processor.add_timestamp(frame)
            
            # Detecta rostos
            faces, gray = self.face_recognizer.detect_faces(frame, MIN_FACE_SIZE)
            
            # Limpa sessões antigas
            self.ponto_manager.cleanup_old_sessions()
            
            # Processa cada rosto detectado
            for face_coords in faces:
                x, y, w, h = face_coords
                
                # Reconhece o rosto
                nome, confidence = self.face_recognizer.recognize_face(gray, face_coords)
                
                if nome:
                    # Pessoa reconhecida
                    registered, recognition_time = self.process_recognition_with_timer(nome, confidence)
                    
                    # Cor da caixa: verde se registrado, azul se em progresso
                    color = (0, 255, 0) if registered else (255, 165, 0)
                    
                    # Desenha caixa e nome
                    label = f"{nome} ({confidence:.1f})"
                    self.frame_processor.draw_face_box(frame, face_coords, label, color, 3)
                    
                    # Mostra progresso se ainda reconhecendo
                    if recognition_time < self.ponto_manager.RECOGNITION_TIME_REQUIRED:
                        progress = recognition_time / self.ponto_manager.RECOGNITION_TIME_REQUIRED
                        self.frame_processor.draw_recognition_progress(
                            frame, progress, nome, (x, y + h + 10)
                        )
                    
                else:
                    # Rosto não reconhecido
                    self.frame_processor.draw_face_box(
                        frame, face_coords, "Desconhecido", (0, 0, 255), 2
                    )
            
            # Mostra sessões ativas
            active_sessions = self.ponto_manager.get_active_sessions()
            if active_sessions:
                info_lines = []
                for nome, session_info in active_sessions.items():
                    remaining = session_info['time_remaining']
                    info_lines.append(f"Reconhecendo {nome}: {remaining:.1f}s restantes")
                
                if info_lines:
                    info_text = '\n'.join(info_lines)
                    self.frame_processor.draw_info_panel(frame, info_text, (10, 70))
            
            # Mostra último reconhecimento
            if self.last_recognition["nome"]:
                last_text = f"Ultimo: {self.last_recognition['nome']} - {self.last_recognition['horario']}"
                cv2.putText(frame, last_text, (10, frame.shape[0] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            # Codifica frame para streaming
            frame_bytes = self.frame_processor.encode_frame_for_web(frame)
            if frame_bytes:
                yield self.frame_processor.create_web_stream_frame(frame_bytes)
    
    def get_last_recognition(self):
        """Retorna o último reconhecimento"""
        return self.last_recognition
    
    def get_pontos_today(self):
        """Retorna pontos do dia atual"""
        return self.ponto_manager.get_pontos_today()
    
    def get_registered_names(self):
        """Retorna nomes cadastrados"""
        return self.face_recognizer.get_registered_names()
    
    def get_statistics(self):
        """Retorna estatísticas"""
        return self.ponto_manager.get_statistics_today()
    
    def stop(self):
        """Para o sistema"""
        self.is_running = False
        self.camera_manager.release()

# Instância global do sistema
face_system = None

def get_face_system():
    """Função para obter instância do sistema (lazy loading)"""
    global face_system
    if face_system is None:
        face_system = FaceRecognitionSystem()
    return face_system

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/registro')
def registro():
    """Página de registro de novas pessoas"""
    return render_template('registro.html')

@app.route('/video_feed')
def video_feed():
    """Stream de vídeo com reconhecimento facial"""
    system = get_face_system()
    return Response(system.generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_registro')
def video_feed_registro():
    """Stream de vídeo para registro (sem reconhecimento)"""
    system = get_face_system()
    return Response(generate_registration_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/last_recognition')
def last_recognition():
    """API para obter último reconhecimento"""
    system = get_face_system()
    return jsonify(system.get_last_recognition())

@app.route('/api/pontos_hoje')
def pontos_hoje():
    """API para obter pontos de hoje"""
    system = get_face_system()
    pontos = system.get_pontos_today()
    return jsonify(pontos)

@app.route('/api/pessoas')
def pessoas():
    """API para obter lista de pessoas cadastradas"""
    system = get_face_system()
    return jsonify(system.get_registered_names())

@app.route('/api/statistics')
def statistics():
    """API para obter estatísticas"""
    system = get_face_system()
    return jsonify(system.get_statistics())

@app.route('/api/pessoas_registradas')
def pessoas_registradas():
    """API para obter pessoas já registradas com contagem de imagens"""
    registration = FaceRegistration(DATA_DIR)
    pessoas = registration.list_registered_people()
    return jsonify(pessoas)

@app.route('/api/registrar_pessoa', methods=['POST'])
def registrar_pessoa():
    """API para registrar nova pessoa"""
    try:
        data = request.get_json()
        nome = data.get('nome', '').strip()
        
        if not nome:
            return jsonify({'success': False, 'message': 'Nome é obrigatório'}), 400
        
        registration = FaceRegistration(DATA_DIR)
        created, message = registration.create_person_folder(nome)
        
        return jsonify({
            'success': True,
            'message': message,
            'created': created
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/capturar_foto', methods=['POST'])
def capturar_foto():
    """API para capturar foto durante registro"""
    try:
        data = request.get_json()
        nome = data.get('nome', '').strip()
        
        if not nome:
            return jsonify({'success': False, 'message': 'Nome é obrigatório'}), 400
        
        # Pega frame atual da câmera
        system = get_face_system()
        frame = system.camera_manager.get_current_frame()
        
        if frame is None:
            return jsonify({'success': False, 'message': 'Nenhum frame disponível'}), 400
        
        registration = FaceRegistration(DATA_DIR)
        
        # Detecta rostos no frame
        faces = registration.detector.detect_faces(frame)
        
        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'Nenhum rosto detectado'}), 400
        
        if len(faces) > 1:
            return jsonify({'success': False, 'message': 'Múltiplos rostos detectados. Certifique-se de que apenas uma pessoa está visível'}), 400
        
        # Salva a foto com o rosto detectado
        face_coords = faces[0]
        success, filepath, count = registration.save_face_image(frame, nome, face_coords)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Foto {count} capturada com sucesso!',
                'filepath': filepath,
                'count': count
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao salvar foto'}), 500
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def generate_registration_frames():
    """Gera frames para a tela de registro"""
    system = get_face_system()
    registration = FaceRegistration(DATA_DIR)
    
    while True:
        success, frame = system.camera_manager.read_frame()
        if not success:
            time.sleep(0.1)
            continue
        
        # Adiciona timestamp
        frame = system.frame_processor.add_timestamp(frame)
        
        # Detecta rostos
        faces = registration.detector.detect_faces(frame)
        
        # Desenha caixas ao redor dos rostos
        for face_coords in faces:
            color = (0, 255, 0) if len(faces) == 1 else (0, 165, 255)  # Verde se 1 rosto, azul se múltiplos
            label = "Pronto para capturar" if len(faces) == 1 else f"Rostos: {len(faces)}"
            system.frame_processor.draw_face_box(frame, face_coords, label, color, 2)
        
        # Adiciona instruções
        if len(faces) == 0:
            cv2.putText(frame, "Posicione seu rosto na camera", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        elif len(faces) > 1:
            cv2.putText(frame, "Apenas uma pessoa por vez", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        else:
            cv2.putText(frame, "Clique em 'Capturar Foto' para registrar", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Codifica frame para streaming
        frame_bytes = system.frame_processor.encode_frame_for_web(frame)
        if frame_bytes:
            yield system.frame_processor.create_web_stream_frame(frame_bytes)

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    finally:
        # Cleanup
        if face_system:
            face_system.stop()