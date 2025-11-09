"""
Aplicação Flask para Sistema de Reconhecimento Facial
"""
from flask import Flask, render_template, Response, jsonify, request
import cv2
import os
from datetime import datetime
from src.models.db import get_db, init_db
from src.models.models import Usuario, PontoUsuario

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Inicializa o banco de dados
init_db()

# Variável global para câmera
camera = None


def get_camera():
    """Obtém instância da câmera (singleton)"""
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    return camera


def generate_frames():
    """Gera frames da câmera para streaming de vídeo"""
    cam = get_camera()
    
    while True:
        success, frame = cam.read()
        if not success:
            break
        
        # Aqui você adicionará o algoritmo de reconhecimento facial posteriormente
        # Por enquanto, apenas exibe o frame da câmera
        
        # Adiciona texto informativo
        cv2.putText(frame, 'Sistema de Reconhecimento Facial', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, 'Aguardando implementacao do algoritmo...', 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Codifica frame para JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Retorna frame no formato multipart
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def generate_frames_registro():
    """Gera frames da câmera para página de registro"""
    cam = get_camera()
    
    while True:
        success, frame = cam.read()
        if not success:
            break
        
        # Detecta faces para auxiliar no cadastro (usando Haar Cascade simples)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Desenha retângulos ao redor das faces detectadas
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, 'Rosto Detectado', (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Adiciona instruções
        cv2.putText(frame, 'Posicione seu rosto no centro', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Codifica frame para JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


# ==================== ROTAS DE PÁGINAS ====================

@app.route('/')
def index():
    """Página principal - Reconhecimento Facial"""
    return render_template('index_client.html')


@app.route('/registro')
def registro():
    """Página de registro de novos usuários"""
    return render_template('registro_client.html')


# ==================== ROTAS DE VÍDEO ====================

@app.route('/video_feed')
def video_feed():
    """Stream de vídeo para reconhecimento"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed_registro')
def video_feed_registro():
    """Stream de vídeo para registro"""
    return Response(generate_frames_registro(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


# ==================== ROTAS DE API ====================

@app.route('/api/pessoas', methods=['GET'])
def api_pessoas():
    """Retorna lista de pessoas cadastradas"""
    with get_db() as db:
        usuarios = db.query(Usuario).filter(Usuario.ativo == True).all()
        nomes = [usuario.nome for usuario in usuarios]
    return jsonify(nomes)


@app.route('/api/pessoas_registradas', methods=['GET'])
def api_pessoas_registradas():
    """Retorna pessoas registradas com detalhes"""
    with get_db() as db:
        usuarios = db.query(Usuario).all()
        pessoas = []
        for usuario in usuarios:
            pessoas.append({
                'nome': usuario.nome,
                'cpf': usuario.cpf,
                'matricula': usuario.matricula,
                'imagens': 1  # Placeholder - será atualizado quando implementar armazenamento de fotos
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
    """Cadastra novo usuário no sistema"""
    data = request.json
    
    nome = data.get('nome', '').strip()
    cpf = data.get('cpf', '').strip()
    matricula = data.get('matricula', '').strip()
    
    # Validações
    if not nome or not cpf or not matricula:
        return jsonify({
            'success': False,
            'message': 'Todos os campos são obrigatórios'
        }), 400
    
    # Remove caracteres especiais do CPF
    cpf = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf) != 11:
        return jsonify({
            'success': False,
            'message': 'CPF inválido'
        }), 400
    
    with get_db() as db:
        # Verifica se CPF já existe
        usuario_existente = db.query(Usuario).filter(Usuario.cpf == cpf).first()
        if usuario_existente:
            return jsonify({
                'success': False,
                'message': 'CPF já cadastrado'
            }), 400
        
        # Verifica se matrícula já existe
        matricula_existente = db.query(Usuario).filter(Usuario.matricula == matricula).first()
        if matricula_existente:
            return jsonify({
                'success': False,
                'message': 'Matrícula já cadastrada'
            }), 400
        
        # Cria novo usuário
        novo_usuario = Usuario(
            nome=nome,
            cpf=cpf,
            matricula=matricula,
            email=data.get('email')
        )
        
        db.add(novo_usuario)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuário {nome} cadastrado com sucesso!',
            'usuario_id': novo_usuario.id
        })


@app.route('/api/capturar_foto', methods=['POST'])
def api_capturar_foto():
    """Captura foto do usuário para treinamento (a ser implementado)"""
    data = request.json
    usuario_id = data.get('usuario_id')
    
    if not usuario_id:
        return jsonify({
            'success': False,
            'message': 'ID do usuário não fornecido'
        }), 400
    
    # TODO: Implementar captura e armazenamento da foto
    # TODO: Processar encoding facial
    
    return jsonify({
        'success': True,
        'message': 'Foto capturada! (implementação pendente)',
        'count': 0
    })


# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
