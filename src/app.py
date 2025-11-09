"""
Aplicação Flask para Sistema de Reconhecimento Facial
"""
from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import base64
import os
from datetime import datetime
from models.db import get_db, init_db
from models.models import Usuario, PontoUsuario
from services.face_recognition_service import get_face_service

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

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
        
        # Codifica frame processado de volta para JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return jsonify({'success': False, 'message': 'Falha ao codificar frame'}), 500
        
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'processed_frame': f'data:image/jpeg;base64,{frame_base64}'
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
        
        # Adiciona instruções
        cv2.putText(frame, 'Posicione seu rosto no centro', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
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


@app.route('/api/capturar_foto', methods=['POST'])
def api_capturar_foto():
    """Captura foto atual da câmera e salva em pasta por CPF.
    Corpo: { usuario_id }
    Retorna: { success, message, count, path }
    """
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
        os.makedirs(rostos_dir, exist_ok=True)

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

        # Salva somente o rosto (200x200, escala de cinza equalizada)
        saved = cv2.imwrite(filepath, face_img)
        if not saved:
            return jsonify({'success': False, 'message': 'Falha ao salvar imagem'}), 500

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


# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
