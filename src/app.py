"""
Aplicação Flask para Sistema de Reconhecimento Facial
"""
from flask import Flask, render_template, Response, jsonify, request, session, redirect, url_for
import cv2
import numpy as np
import base64
import os
from datetime import datetime, timedelta
from models.db import get_db, init_db
from models.models import Usuario, PontoUsuario, UsuarioLogin, TipoUsuario
from services.face_recognition_service import get_face_service
from sqlalchemy import func, and_, extract
from functools import wraps
from constants.config import ESP32_CAM_URL as CFG_ESP32_CAM_URL
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen, Request
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'face-recognition-secret-key-2025'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Adiciona headers para permitir acesso à câmera
@app.after_request
def add_security_headers(response):
    # Permite acesso a recursos de mídia
    response.headers['Permissions-Policy'] = 'camera=*, microphone=*'
    return response

# Inicializa o banco de dados
init_db()

# Variável global para serviço de reconhecimento facial
face_service = get_face_service()

# Classificador Haar para reutilização em todo o módulo (evita recriar a cada frame)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Cache do último frame capturado (evita competição pela câmera)
import threading
last_frame_lock = threading.Lock()
last_frame_cache = None
last_frame_registro_cache = None


def _detect_largest_face_bbox(gray):
    """Detecta faces e retorna o bounding box da maior face.
    Retorna tupla (x, y, w, h) ou None se não encontrar.
    """
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    # Seleciona a maior face por área
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return (x, y, w, h)


def _crop_face_from_frame(frame, margin: float = 0.15, return_color: bool = False):
    """Recorta somente o rosto a partir do frame, com pequena margem.
    - Detecta a maior face em escala de cinza
    - Aplica margem percentual
    - Redimensiona para 200x200
    - Se return_color=True retorna imagem BGR 200x200
    - Caso contrário retorna grayscale equalizada 200x200
    Retorna ndarray ou None.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bbox = _detect_largest_face_bbox(gray)
    if bbox is None:
        return None
    x, y, w, h = bbox
    mh = int(h * margin)
    mw = int(w * margin)
    x1 = max(0, x - mw)
    y1 = max(0, y - mh)
    x2 = min(gray.shape[1], x + w + mw)
    y2 = min(gray.shape[0], y + h + mh)
    if return_color:
        face_color = frame[y1:y2, x1:x2]
        if face_color.size == 0:
            return None
        face_color = cv2.resize(face_color, (200, 200))
        return face_color
    else:
        face_gray = gray[y1:y2, x1:x2]
        if face_gray.size == 0:
            return None
        face_gray = cv2.resize(face_gray, (200, 200))
        face_gray = cv2.equalizeHist(face_gray)
        return face_gray


# ==================== ROTAS DE PÁGINAS ====================

@app.route('/')
def index():
    """Página principal - Reconhecimento Facial"""
    return render_template('index.html')


@app.route('/registro')
def registro():
    """Página de registro de novos usuários"""
    return render_template('registro.html')


@app.route('/espcam')
def index_espcam():
    """Página de visualização da ESP32-CAM (stream estático)."""
    return render_template('index_espcam.html', stream_url=CFG_ESP32_CAM_URL)


@app.route('/registro_espcam')
def registro_espcam():
    """Página de registro usando stream da ESP32-CAM (somente exibição do stream)."""
    return render_template('registro_espcam.html', stream_url=CFG_ESP32_CAM_URL)


# ==================== AUTENTICAÇÃO ====================

def login_required(f):
    """Decorator para rotas que exigem login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator para rotas que exigem admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        with get_db() as db:
            user = db.query(UsuarioLogin).filter(UsuarioLogin.id == session['user_id']).first()
            if not user or not user.is_admin():
                return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/visualizar_dados')
def visualizar_dados():
    """Redireciona para login se não autenticado, senão para dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login')
def login():
    """Página de login"""
    return render_template('login.html')


@app.route('/registro_usuario')
def registro_usuario():
    """Página de registro de usuário"""
    return render_template('registro_usuario.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard do usuário (admin ou padrão)"""
    with get_db() as db:
        user = db.query(UsuarioLogin).filter(UsuarioLogin.id == session['user_id']).first()
        if not user:
            session.clear()
            return redirect(url_for('login'))
        
        return render_template('dashboard.html', usuario=user)


@app.route('/logout')
def logout():
    """Logout do usuário"""
    session.clear()
    return redirect(url_for('index'))


def _derive_snapshot_url(stream_url: str) -> str:
    """Deriva a URL de snapshot (/capture) a partir da URL do stream fornecida.
    Convenções usuais do firmware da Arduino (CameraWebServer):
      - Página HTML: http://IP/
      - Snapshot:    http://IP/capture (porta 80)
      - Stream MJPEG:http://IP:81/stream (porta 81)
    """
    try:
        p = urlparse(stream_url)
        # Base host (sem porta 81)
        host = p.hostname or 'localhost'
        scheme = p.scheme or 'http'
        # Se porta é 81, snapshot costuma estar no 80
        netloc = host
        if p.port and p.port != 80:
            # Assume snapshot na 80
            netloc = host
        # Caminho padrão do snapshot
        snapshot_path = '/capture'
        return urlunparse((scheme, netloc, snapshot_path, '', '', ''))
    except Exception:
        # Fallback simples
        return stream_url.rstrip('/') + '/capture'


@app.route('/api/espcam/snapshot')
def api_espcam_snapshot():
    """Proxy de snapshot para ESP32-CAM. Evita CORS no browser.
    Retorna image/jpeg.
    """
    url = _derive_snapshot_url(CFG_ESP32_CAM_URL)
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=3) as resp:
            data = resp.read()
            return Response(data, mimetype='image/jpeg')
    except (Exception, socket.timeout) as e:
        return jsonify({'success': False, 'message': f'ESP32 snapshot indisponível: {str(e)}'}), 502


# ==================== ROTAS DE VÍDEO ====================

@app.route('/api/process_frame', methods=['POST'])
def api_process_frame():

    """Processa frame enviado pelo cliente para reconhecimento"""
    try:
        data = request.json or {}
        frame_data = data.get('frame')
        
        if not frame_data:
            return jsonify({'success': False, 'message': 'Frame não fornecido'}), 400
        
        # Decodifica base64 para imagem
        img_data = base64.b64decode(frame_data.split(',')[1] if ',' in frame_data else frame_data)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'message': 'Falha ao decodificar frame'}), 400
        
        # Atualiza cache do último frame
        global last_frame_cache
        with last_frame_lock:
            last_frame_cache = frame.copy()
        
        # Executa detecção e reconhecimento
        face_service.detect_and_recognize(frame)
        ui = face_service.get_ui_status()
        
        # Codifica frame processado de volta para JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return jsonify({'success': False, 'message': 'Falha ao codificar frame'}), 500
        
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'processed_frame': f'data:image/jpeg;base64,{frame_base64}',
            'ui': ui
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@app.route('/api/process_frame_registro', methods=['POST'])
def api_process_frame_registro():
    """Processa frame enviado pelo cliente para registro"""
    try:
        data = request.json or {}
        frame_data = data.get('frame')
        
        if not frame_data:
            return jsonify({'success': False, 'message': 'Frame não fornecido'}), 400
        
        # Decodifica base64 para imagem
        img_data = base64.b64decode(frame_data.split(',')[1] if ',' in frame_data else frame_data)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'message': 'Falha ao decodificar frame'}), 400
        
        # Atualiza cache do último frame
        global last_frame_registro_cache
        with last_frame_lock:
            last_frame_registro_cache = frame.copy()
        
        # Detecta faces para auxiliar no cadastro
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        
        # Desenha retângulos ao redor das faces detectadas
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, 'Rosto Detectado', (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Adiciona instruções na parte superior
        cv2.putText(frame, 'Posicione seu rosto no centro', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Codifica frame processado de volta para JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return jsonify({'success': False, 'message': 'Falha ao codificar frame'}), 500
        
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'processed_frame': f'data:image/jpeg;base64,{frame_base64}',
            'faces_detected': len(faces)
        })
        
    except Exception as e:
        print(f"[ERRO] process_frame_registro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


# ==================== ROTAS DE API ====================

@app.route('/api/pessoas', methods=['GET'])
def api_pessoas():
    """Retorna lista de pessoas cadastradas"""
    with get_db() as db:
        usuarios = db.query(Usuario).all()
        nomes = [usuario.nome for usuario in usuarios]
    return jsonify(nomes)


@app.route('/api/pessoas_registradas', methods=['GET'])
def api_pessoas_registradas():
    """Retorna pessoas registradas com detalhes"""
    with get_db() as db:
        usuarios = db.query(Usuario).all()
        pessoas = []
        for usuario in usuarios:
            # Conta imagens reais na pasta do CPF
            base_dir = os.path.join(os.path.dirname(__file__), 'constants', 'rostos', usuario.cpf)
            count_imgs = 0
            if os.path.isdir(base_dir):
                count_imgs = len([f for f in os.listdir(base_dir) if f.lower().endswith('.jpg')])
            pessoas.append({
                'nome': usuario.nome,
                'cpf': usuario.cpf,
                'matricula': usuario.matricula,
                'imagens': count_imgs
            })
    return jsonify(pessoas)


@app.route('/api/pontos_hoje', methods=['GET'])
def api_pontos_hoje():
    """Retorna pontos registrados hoje"""
    with get_db() as db:
        hoje = datetime.now().date()
        pontos = db.query(PontoUsuario).join(Usuario).filter(
            PontoUsuario.data_hora >= datetime.combine(hoje, datetime.min.time())
        ).order_by(PontoUsuario.data_hora.desc()).all()
        
        resultado = []
        for ponto in pontos:
            resultado.append({
                'nome': ponto.usuario.nome,
                'hora': ponto.data_hora.strftime('%H:%M:%S'),
                'confianca': ponto.confianca
            })
    
    return jsonify(resultado)


@app.route('/api/last_recognition', methods=['GET'])
def api_last_recognition():
    """Retorna o último reconhecimento realizado"""
    with get_db() as db:
        ultimo_ponto = db.query(PontoUsuario).join(Usuario).order_by(
            PontoUsuario.data_hora.desc()
        ).first()
        
        if ultimo_ponto:
            return jsonify({
                'nome': ultimo_ponto.usuario.nome,
                'horario': ultimo_ponto.data_hora.isoformat(),
                'confianca': ultimo_ponto.confianca
            })
        
    return jsonify({'nome': None})


@app.route('/api/cadastrar_usuario', methods=['POST'])
def api_cadastrar_usuario():
    """(Deprecated) Endpoint antigo de cadastro isolado. Prefira /api/usuario_status"""
    data = request.json or {}
    return usuario_status_internal(data, legacy=True)


@app.route('/api/usuario_status', methods=['POST'])
def api_usuario_status():
    """Verifica se usuário existe (por CPF ou matrícula) e cria se não existir.
    Retorna: { success, new_user: bool, usuario_id, message, cpf }
    """
    data = request.json or {}
    return usuario_status_internal(data)


def usuario_status_internal(data, legacy: bool = False):
    try:
        nome = (data.get('nome') or '').strip()
        cpf_raw = (data.get('cpf') or '').strip()
        matricula = (data.get('matricula') or '').strip()
        email = (data.get('email') or '').strip() or None

        # Normaliza CPF
        cpf = ''.join(filter(str.isdigit, cpf_raw))

        if not nome or not cpf or not matricula:
            return jsonify({
                'success': False,
                'message': 'Todos os campos (nome, cpf, matrícula) são obrigatórios'
            }), 400

        if len(cpf) != 11:
            return jsonify({
                'success': False,
                'message': 'CPF inválido'
            }), 400

        with get_db() as db:
            # Procura usuário por CPF ou matrícula
            usuario = db.query(Usuario).filter((Usuario.cpf == cpf) | (Usuario.matricula == matricula)).first()
            if usuario:
                return jsonify({
                    'success': True,
                    'new_user': False,
                    'usuario_id': usuario.id,
                    'cpf': usuario.cpf,
                    'message': 'Usuário existente. Prossiga para captura de fotos.'
                })

            # Verifica duplicações específicas
            dup_cpf = db.query(Usuario).filter(Usuario.cpf == cpf).first()
            if dup_cpf:
                return jsonify({
                    'success': False,
                    'message': 'CPF já cadastrado em outro registro'
                }), 400
            dup_mat = db.query(Usuario).filter(Usuario.matricula == matricula).first()
            if dup_mat:
                return jsonify({
                    'success': False,
                    'message': 'Matrícula já cadastrada em outro registro'
                }), 400

            # Cria novo usuário
            novo = Usuario(nome=nome, cpf=cpf, matricula=matricula, email=email)
            db.add(novo)
            db.commit()
            return jsonify({
                'success': True,
                'new_user': True,
                'usuario_id': novo.id,
                'cpf': novo.cpf,
                'message': 'Usuário novo criado. Prossiga para captura de fotos.'
            })
    except Exception as e:
        # Log simples no console; poderia usar logging estruturado
        print(f"[ERRO] usuario_status_internal: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao verificar usuário'}), 500


@app.route('/api/capturar_foto', methods=['POST'])
def api_capturar_foto():
    """Captura foto atual da câmera e salva em pasta por CPF.
    Corpo: { usuario_id }
    Retorna: { success, message, count, path }
    """
    try:
        data = request.json or {}
        usuario_id = data.get('usuario_id')
        if not usuario_id:
            return jsonify({'success': False, 'message': 'ID do usuário não fornecido'}), 400

        with get_db() as db:
            usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not usuario:
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404

            cpf = usuario.cpf
            # Pasta de rostos dentro de src/constants/rostos/<cpf>
            base_dir = os.path.dirname(__file__)  # src
            rostos_dir = os.path.join(base_dir, 'constants', 'rostos', cpf)
            
            # Cria pasta se não existir
            try:
                os.makedirs(rostos_dir, exist_ok=True)
                print(f"[INFO] Pasta criada/confirmada: {rostos_dir}")
            except Exception as dir_err:
                print(f"[ERRO] Falha ao criar pasta {rostos_dir}: {dir_err}")
                return jsonify({'success': False, 'message': f'Erro ao criar pasta: {str(dir_err)}'}), 500

            # Usa o frame do cache ao invés de capturar diretamente da câmera
            with last_frame_lock:
                frame = last_frame_registro_cache.copy() if last_frame_registro_cache is not None else None
            
            if frame is None:
                return jsonify({'success': False, 'message': 'Nenhum frame disponível. Aguarde o stream carregar.'}), 500

            # Recorta somente a região do rosto (bounding box) para usar no treinamento
            face_img = _crop_face_from_frame(frame, margin=0.15, return_color=True)
            if face_img is None:
                return jsonify({'success': False, 'message': 'Nenhum rosto detectado. Tente ajustar o enquadramento/iluminação.'}), 400

            # Nome do arquivo
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            existing = len([f for f in os.listdir(rostos_dir) if f.lower().endswith('.jpg')])
            filename = f"{cpf}_{existing+1}_{timestamp}.jpg"
            filepath = os.path.join(rostos_dir, filename)

            # Salva somente o rosto (200x200, BGR)
            saved = cv2.imwrite(filepath, face_img)
            if not saved:
                print(f"[ERRO] Falha ao salvar {filepath}")
                return jsonify({'success': False, 'message': 'Falha ao salvar imagem'}), 500

            print(f"[INFO] Foto salva: {filepath}")

            # Atualiza caminho principal se vazio
            if not usuario.foto_path:
                usuario.foto_path = rostos_dir
            db.add(usuario)
            db.commit()

            total = len([f for f in os.listdir(rostos_dir) if f.lower().endswith('.jpg')])
            rel_path = os.path.relpath(filepath, base_dir)

            return jsonify({
                'success': True,
                'message': 'Foto capturada e salva com sucesso',
                'count': total,
                'path': rel_path
            })
    except Exception as e:
        print(f"[ERRO] api_capturar_foto: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro ao capturar foto: {str(e)}'}), 500


@app.route('/api/recriar_modelo', methods=['POST'])
def api_recriar_modelo():
    qtd = face_service.train()
    return jsonify({'success': True, 'message': f'Modelo re-treinado com {qtd} imagens.'})


@app.route('/api/model_status', methods=['GET'])
def api_model_status():
    """Retorna informações do modelo treinado e dataset."""
    base = os.path.join(os.path.dirname(__file__), 'constants', 'rostos')
    status = {
        'trained': face_service.is_trained(),
        'threshold': face_service.get_threshold(),
        'datasets': []
    }
    if os.path.isdir(base):
        for cpf in sorted(os.listdir(base)):
            pasta = os.path.join(base, cpf)
            if not os.path.isdir(pasta):
                continue
            count_imgs = len([f for f in os.listdir(pasta) if f.lower().endswith('.jpg')])
            status['datasets'].append({'cpf': cpf, 'imagens': count_imgs})
    return jsonify(status)


@app.route('/api/ajustar_limite', methods=['POST'])
def api_ajustar_limite():
    """Ajusta o limiar de confiança do reconhecimento (quanto menor, mais estrito)."""
    data = request.json or {}
    novo = data.get('threshold')
    if novo is None:
        return jsonify({'success': False, 'message': 'Forneça threshold numérico.'}), 400
    try:
        v = float(novo)
    except Exception:
        return jsonify({'success': False, 'message': 'Threshold inválido.'}), 400
    value = face_service.set_threshold(v)
    return jsonify({'success': True, 'threshold': value})


@app.route('/api/predict_now', methods=['GET'])
def api_predict_now():
    """Executa predição no frame atual e retorna detalhes (para depuração)."""
    # Usa o frame do cache ao invés de capturar diretamente
    with last_frame_lock:
        frame = last_frame_cache.copy() if last_frame_cache is not None else None
    
    if frame is None:
        return jsonify({'success': False, 'message': 'Nenhum frame disponível no cache'}), 500
    
    result = face_service.debug_predict(frame)
    return jsonify({'success': True, 'result': result})


@app.route('/api/ajustar_tempos', methods=['POST'])
def api_ajustar_tempos():
    """Ajusta tempos de UX: estabilidade antes de detectar e cooldown pós-detecção.
    Body: { stable_seconds?: number, cooldown_seconds?: number }
    """
    data = request.json or {}
    face_service.set_timing(
        stable_seconds=data.get('stable_seconds'),
        cooldown_seconds=data.get('cooldown_seconds')
    )
    return jsonify({
        'success': True,
        'stable_seconds': face_service.stable_seconds,
        'cooldown_seconds': face_service.cooldown_seconds
    })


@app.route('/api/last_detection', methods=['GET'])
def api_last_detection():
    data = face_service.pop_last_detection()
    if not data:
        return jsonify({'found': False})
    # Busca usuário por CPF
    with get_db() as db:
        usuario = db.query(Usuario).filter(Usuario.cpf == data['cpf']).first()
        if not usuario:
            return jsonify({'found': False})
        return jsonify({
            'found': True,
            'cpf': usuario.cpf,
            'nome': usuario.nome,
            'matricula': usuario.matricula,
            'horario': data['timestamp'],
            'confidence': data['confidence'],
            'detection_id': data.get('detection_id')
        })


@app.route('/api/confirmar_ponto', methods=['POST'])
def api_confirmar_ponto():
    try:
        body = request.json or {}
        cpf = body.get('cpf')
        if not cpf:
            return jsonify({'success': False, 'message': 'CPF não fornecido'}), 400
        # Consome detecção pendente se houver detection_id, senão realiza captura direta
        detection_id = body.get('detection_id')
        # Confiança pode vir string; tenta converter
        confidence = body.get('confidence')
         
        try:
            confidence = float(confidence) if confidence is not None else None
        except Exception:
            confidence = None

        with get_db() as db:
            usuario = db.query(Usuario).filter(Usuario.cpf == cpf).first()
            if not usuario:
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
            foto_registro_rel = None
            if detection_id:
                det = face_service.consume_detection(detection_id)
                if det and det.get('cpf') == cpf:
                    base_dir = os.path.join(os.path.dirname(__file__), 'constants', 'rostos', cpf)
                    os.makedirs(base_dir, exist_ok=True)
                    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f'confirm_{ts}.jpg'
                    filepath = os.path.join(base_dir, filename)
                    img = det.get('roi_color')
                    if img is not None:
                        try:
                            cv2.imwrite(filepath, img)
                            foto_registro_rel = os.path.relpath(filepath, os.path.dirname(__file__))
                        except Exception as e:
                            # Continua sem abortar; tenta fallback com frame atual
                            print(f"[confirmar_ponto] Erro ao salvar ROI: {e}")
            if not foto_registro_rel:
                # Fallback: captura frame atual, recorta e salva
                with last_frame_lock:
                    frame = last_frame_cache.copy() if last_frame_cache is not None else None
                
                if frame is None:
                    return jsonify({'success': False, 'message': 'Nenhum frame disponível no cache'}), 500
                
                face_img = _crop_face_from_frame(frame, margin=0.15, return_color=True)
                if face_img is None:
                    return jsonify({'success': False, 'message': 'Nenhum rosto detectado para confirmação'}), 400
                base_dir = os.path.join(os.path.dirname(__file__), 'constants', 'rostos', cpf)
                os.makedirs(base_dir, exist_ok=True)
                ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
                filename = f'confirm_{ts}.jpg'
                filepath = os.path.join(base_dir, filename)
                cv2.imwrite(filepath, face_img)
                foto_registro_rel = os.path.relpath(filepath, os.path.dirname(__file__))
            if not usuario.foto_path:
                usuario.foto_path = os.path.join(os.path.dirname(__file__), 'constants', 'rostos', cpf)
            ponto = PontoUsuario(usuario_id=usuario.id, confianca=confidence, foto_registro_path=foto_registro_rel)
            db.add(ponto)
            db.add(usuario)
            db.commit()
        return jsonify({'success': True, 'message': 'Ponto registrado com sucesso.'})
    except Exception as e:
        # Garante resposta JSON para evitar erro de parse no frontend
        print(f"[confirmar_ponto] Erro inesperado: {e}")
        return jsonify({'success': False, 'message': f'Erro interno ao registrar ponto: {str(e)}'}), 500


# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route('/api/register', methods=['POST'])
def api_register():
    """Registra novo usuário"""
    try:
        data = request.json or {}
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        cpf = data.get('cpf', '').strip()
        
        if not username or not email or not password:
            return jsonify({'success': False, 'message': 'Username, email e senha são obrigatórios'}), 400
        
        # Limpa CPF se fornecido
        cpf_clean = ''.join(filter(str.isdigit, cpf)) if cpf else None
        if cpf_clean and len(cpf_clean) != 11:
            return jsonify({'success': False, 'message': 'CPF deve ter 11 dígitos'}), 400
        
        with get_db() as db:
            # Verifica se username já existe
            if db.query(UsuarioLogin).filter(UsuarioLogin.username == username).first():
                return jsonify({'success': False, 'message': 'Nome de usuário já existe'}), 400
            
            # Verifica se email já existe
            if db.query(UsuarioLogin).filter(UsuarioLogin.email == email).first():
                return jsonify({'success': False, 'message': 'Email já cadastrado'}), 400
            
            # Verifica se CPF já está vinculado
            if cpf_clean and db.query(UsuarioLogin).filter(UsuarioLogin.cpf == cpf_clean).first():
                return jsonify({'success': False, 'message': 'CPF já está vinculado a outra conta'}), 400
            
            # Cria novo usuário
            new_user = UsuarioLogin(
                username=username,
                email=email,
                cpf=cpf_clean,
                tipo=TipoUsuario.DEFAULT
            )
            new_user.set_password(password)
            
            db.add(new_user)
            db.commit()
            
            return jsonify({'success': True, 'message': 'Conta criada com sucesso'})
            
    except Exception as e:
        print(f"[ERRO] api_register: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@app.route('/api/login', methods=['POST'])
def api_login():
    """Autentica usuário"""
    try:
        data = request.json or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username e senha são obrigatórios'}), 400
        
        with get_db() as db:
            user = db.query(UsuarioLogin).filter(
                UsuarioLogin.username == username,
                UsuarioLogin.ativo == True
            ).first()
            
            if not user or not user.check_password(password):
                return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401
            
            # Atualiza último login
            user.ultimo_login = datetime.utcnow()
            db.commit()
            
            # Cria sessão
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin()
            
            return jsonify({
                'success': True, 
                'message': 'Login realizado com sucesso',
                'redirect_url': '/dashboard'
            })
            
    except Exception as e:
        print(f"[ERRO] api_login: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


# ==================== ROTAS DO DASHBOARD ====================

@app.route('/api/dashboard/meus-pontos')
@login_required
def api_meus_pontos():
    """Retorna pontos do usuário logado"""
    try:
        cpf = request.args.get('cpf')
        if not cpf:
            return jsonify({'success': False, 'message': 'CPF não fornecido'}), 400
        
        with get_db() as db:
            # Verifica se o CPF pertence ao usuário logado
            user = db.query(UsuarioLogin).filter(UsuarioLogin.id == session['user_id']).first()
            if not user or user.cpf != cpf:
                return jsonify({'success': False, 'message': 'Acesso negado'}), 403
            
            # Busca pontos do usuário
            usuario = db.query(Usuario).filter(Usuario.cpf == cpf).first()
            if not usuario:
                return jsonify({'success': True, 'pontos': []})
            
            pontos = db.query(PontoUsuario).filter(
                PontoUsuario.usuario_id == usuario.id
            ).order_by(PontoUsuario.data_hora.desc()).limit(100).all()
            
            pontos_data = [{
                'id': p.id,
                'data_hora': p.data_hora.isoformat(),
                'confianca': p.confianca,
                'dispositivo': p.dispositivo
            } for p in pontos]
            
            return jsonify({'success': True, 'pontos': pontos_data})
            
    except Exception as e:
        print(f"[ERRO] api_meus_pontos: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@app.route('/api/dashboard/ranking')
@admin_required
def api_ranking():
    """Retorna ranking de usuários por horas trabalhadas no mês atual"""
    try:
        with get_db() as db:
            # Mês atual
            now = datetime.utcnow()
            inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Query complexa para calcular horas trabalhadas
            # Assume que pontos pares são entrada e ímpares são saída
            ranking_data = []
            
            usuarios = db.query(Usuario).all()
            for usuario in usuarios:
                pontos_mes = db.query(PontoUsuario).filter(
                    PontoUsuario.usuario_id == usuario.id,
                    PontoUsuario.data_hora >= inicio_mes
                ).order_by(PontoUsuario.data_hora).all()
                
                total_horas = 0
                # Agrupa por dia
                pontos_por_dia = {}
                for ponto in pontos_mes:
                    dia = ponto.data_hora.date()
                    if dia not in pontos_por_dia:
                        pontos_por_dia[dia] = []
                    pontos_por_dia[dia].append(ponto)
                
                # Calcula horas por dia (primeiro e último ponto)
                for dia, pontos_dia in pontos_por_dia.items():
                    if len(pontos_dia) >= 2:
                        entrada = pontos_dia[0].data_hora
                        saida = pontos_dia[-1].data_hora
                        diff = saida - entrada
                        horas = diff.total_seconds() / 3600
                        total_horas += horas
                
                if total_horas > 0:
                    ranking_data.append({
                        'nome': usuario.nome,
                        'cpf': usuario.cpf,
                        'total_horas': round(total_horas, 2)
                    })
            
            # Ordena por horas decrescente e pega top 5
            ranking_data.sort(key=lambda x: x['total_horas'], reverse=True)
            top_5 = ranking_data[:5]
            
            return jsonify({'success': True, 'ranking': top_5})
            
    except Exception as e:
        print(f"[ERRO] api_ranking: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@app.route('/api/dashboard/usuarios-presentes')
@admin_required
def api_usuarios_presentes():
    """Retorna usuários que bateram apenas 1 ponto hoje (estão presentes)"""
    try:
        with get_db() as db:
            hoje = datetime.utcnow().date()
            inicio_dia = datetime.combine(hoje, datetime.min.time())
            fim_dia = datetime.combine(hoje, datetime.max.time())
            
            presentes = []
            usuarios = db.query(Usuario).all()
            
            for usuario in usuarios:
                pontos_hoje = db.query(PontoUsuario).filter(
                    PontoUsuario.usuario_id == usuario.id,
                    PontoUsuario.data_hora >= inicio_dia,
                    PontoUsuario.data_hora <= fim_dia
                ).order_by(PontoUsuario.data_hora).all()
                
                # Se tem exatamente 1 ponto, está presente
                if len(pontos_hoje) == 1:
                    presentes.append({
                        'nome': usuario.nome,
                        'cpf': usuario.cpf,
                        'ultimo_ponto': pontos_hoje[0].data_hora.isoformat()
                    })
            
            return jsonify({'success': True, 'presentes': presentes})
            
    except Exception as e:
        print(f"[ERRO] api_usuarios_presentes: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@app.route('/api/dashboard/resumo-todos')
@admin_required
def api_resumo_todos():
    """Retorna resumo de todos os usuários"""
    try:
        with get_db() as db:
            hoje = datetime.utcnow().date()
            inicio_dia = datetime.combine(hoje, datetime.min.time())
            fim_dia = datetime.combine(hoje, datetime.max.time())
            
            usuarios = db.query(Usuario).all()
            resumo = []
            
            for usuario in usuarios:
                total_pontos = db.query(PontoUsuario).filter(
                    PontoUsuario.usuario_id == usuario.id
                ).count()
                
                ultimo_ponto = db.query(PontoUsuario).filter(
                    PontoUsuario.usuario_id == usuario.id
                ).order_by(PontoUsuario.data_hora.desc()).first()
                
                pontos_hoje = db.query(PontoUsuario).filter(
                    PontoUsuario.usuario_id == usuario.id,
                    PontoUsuario.data_hora >= inicio_dia,
                    PontoUsuario.data_hora <= fim_dia
                ).count()
                
                resumo.append({
                    'nome': usuario.nome,
                    'cpf': usuario.cpf,
                    'total_pontos': total_pontos,
                    'ultimo_ponto': ultimo_ponto.data_hora.isoformat() if ultimo_ponto else None,
                    'pontos_hoje': pontos_hoje
                })
            
            # Ordena por nome
            resumo.sort(key=lambda x: x['nome'])
            
            return jsonify({'success': True, 'usuarios': resumo})
            
    except Exception as e:
        print(f"[ERRO] api_resumo_todos: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
