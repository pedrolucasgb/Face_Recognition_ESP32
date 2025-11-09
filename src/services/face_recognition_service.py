"""Serviço de reconhecimento facial baseado em LBPH.

Responsabilidades:
 - Carregar imagens de rostos em `src/constants/rostos/<cpf>/*.jpg`
 - Treinar modelo LBPH
 - Detectar faces em frames e reconhecer por CPF
 - Expor dados da última detecção (para popup de confirmação)

Observações:
 - Reconhecimentos retornam menor confidence melhor. Limite ajustável.
 - Rosto desconhecido: desenha bounding box vermelha.
"""
from __future__ import annotations
import os
import cv2
import numpy as np
import threading
from datetime import datetime, timedelta
import uuid
from typing import Dict, Optional, Tuple, List

# Parâmetros LBPH (podem ser ajustados conforme qualidade do dataset)
LBPH_PARAMS = dict(radius=2, neighbors=8, grid_x=8, grid_y=8)
DEFAULT_CONFIDENCE_THRESHOLD = 85.0  # <= limite => reconhecido
FACE_SIZE = (60, 60)

class FaceRecognitionService:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir  # caminho absoluto para src/constants/rostos
        self._lock = threading.Lock()
        self._recognizer = None
        self._label_to_cpf: Dict[int, str] = {}
        self._cpf_to_label: Dict[str, int] = {}
        self._nomes: List[str] = []  # apenas referência
        self._face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.last_detection: Optional[Dict] = None  # {'cpf':..., 'confidence':..., 'timestamp':..., 'bbox':(x,y,w,h)}
        self.threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
        # Estabilidade e cooldown
        self.stable_seconds: float = 5.0
        self.cooldown_seconds: float = 5.0
        # Candidato atual: {'cpf':..., 'start': datetime, 'last': datetime, 'best_conf': float, 'bbox': (x,y,w,h)}
        self._current_candidate: Optional[Dict] = None
        # Cooldowns por CPF: cpf -> datetime quando pode disparar novamente
        self._cooldowns: Dict[str, datetime] = {}
        # Detecções pendentes aguardando confirmação: id -> {cpf, roi_color, best_conf, timestamp, bbox}
        self._pending: Dict[str, Dict] = {}
        # Últimos dados para UI
        self._last_faces = 0

    def train(self) -> int:
        """Treina (ou re-treina) o modelo LBPH lendo pastas por CPF.
        Retorna quantidade de rostos carregados.
        """
        imagens = []
        labels = []
        label_counter = 0
        self._label_to_cpf.clear()
        self._cpf_to_label.clear()
        self._nomes.clear()

        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

        for cpf in sorted(os.listdir(self.base_dir)):
            pasta = os.path.join(self.base_dir, cpf)
            if not os.path.isdir(pasta):
                continue
            if cpf not in self._cpf_to_label:
                self._cpf_to_label[cpf] = label_counter
                self._label_to_cpf[label_counter] = cpf
                self._nomes.append(cpf)
                label_counter += 1
            label_id = self._cpf_to_label[cpf]
            for arquivo in os.listdir(pasta):
                if not arquivo.lower().endswith('.jpg'):
                    continue
                caminho = os.path.join(pasta, arquivo)
                img_gray = cv2.imread(caminho, cv2.IMREAD_GRAYSCALE)
                if img_gray is None:
                    continue
                img_gray = cv2.resize(img_gray, (200, 200))
                img_gray = cv2.equalizeHist(img_gray)
                imagens.append(img_gray)
                labels.append(label_id)

        if not imagens:
            # Sem dados - limpa recognizer
            with self._lock:
                self._recognizer = None
            return 0

        recognizer = cv2.face.LBPHFaceRecognizer_create(**LBPH_PARAMS)
        labels_np = np.array(labels, dtype=np.int32)
        recognizer.train(imagens, labels_np)
        with self._lock:
            self._recognizer = recognizer
        return len(imagens)

    def detect_and_recognize(self, frame) -> None:
        """Detecta faces e tenta reconhecer. Atualiza self.last_detection.
        Desenha bounding boxes direto no frame.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=FACE_SIZE)
        # atualiza contagem de faces para UI
        self._last_faces = int(len(faces))
        found = None

        with self._lock:
            recognizer = self._recognizer

        now = datetime.utcnow()
        # Se há candidato e passou muito tempo sem atualização, zera
        if self._current_candidate and (now - self._current_candidate['last']).total_seconds() > 1.5:
            self._current_candidate = None

        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            roi_gray = cv2.resize(roi_gray, (200, 200))
            roi_gray = cv2.equalizeHist(roi_gray)
            roi_color = frame[y:y+h, x:x+w]
            roi_color = cv2.resize(roi_color, (200, 200))
            if recognizer is not None:
                label_id, confidence = recognizer.predict(roi_gray)
                if confidence <= self.threshold and label_id in self._label_to_cpf:
                    cpf = self._label_to_cpf[label_id]
                    # Caixa verde para reconhecido (sem texto)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 180, 0), 2)
                    # Lógica de estabilidade e cooldown
                    cooldown_until = self._cooldowns.get(cpf)
                    if cooldown_until and now < cooldown_until:
                        # Em cooldown: não dispara, só desenha
                        continue
                    cand = self._current_candidate
                    if not cand or cand.get('cpf') != cpf:
                        # Novo candidato
                        self._current_candidate = {
                            'cpf': cpf,
                            'start': now,
                            'last': now,
                            'best_conf': confidence,
                            'bbox': (x, y, w, h),
                            'roi': roi_gray.copy(),
                            'roi_color': roi_color.copy()
                        }
                    else:
                        # Atualiza existente
                        cand['last'] = now
                        if confidence < cand['best_conf']:
                            cand['best_conf'] = confidence
                            cand['bbox'] = (x, y, w, h)
                            cand['roi'] = roi_gray.copy()
                            cand['roi_color'] = roi_color.copy()
                    # Checa se já ficou estável o suficiente
                    cand = self._current_candidate
                    if cand and cand.get('cpf') == cpf:
                        elapsed = (now - cand['start']).total_seconds()
                        if elapsed >= self.stable_seconds and self.last_detection is None:
                            # Não salva imagem aqui. Apenas cria uma detecção pendente com ROI em memória.
                            det_id = str(uuid.uuid4())
                            self._pending[det_id] = {
                                'cpf': cpf,
                                'roi_color': cand.get('roi_color', roi_color).copy(),
                                'best_conf': float(cand['best_conf']),
                                'timestamp': now,
                                'bbox': cand['bbox']
                            }
                            found = {
                                'cpf': cpf,
                                'confidence': float(cand['best_conf']),
                                'timestamp': now.isoformat(),
                                'bbox': cand['bbox'],
                                'detection_id': det_id
                            }
                            # Define cooldown para este CPF
                            self._cooldowns[cpf] = now + timedelta(seconds=self.cooldown_seconds)
                            # Limpa candidato atual
                            self._current_candidate = None
                else:
                    # Desconhecido -> caixa vermelha (sem texto)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
            else:
                # Sem modelo -> caixa vermelha sem texto
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)

        if found and self.last_detection is None:
            self.last_detection = found

    def get_ui_status(self) -> Dict:
        """Retorna informações resumidas para UI: progresso de estabilidade e faces detectadas."""
        now = datetime.utcnow()
        tracking = self._current_candidate is not None
        progress = 0.0
        seconds_left = None
        cooldown_active = False
        if tracking:
            cand = self._current_candidate
            elapsed = (now - cand['start']).total_seconds()
            progress = max(0.0, min(1.0, elapsed / max(0.001, self.stable_seconds)))
            seconds_left = max(0.0, self.stable_seconds - elapsed)
            # cooldown não se aplica enquanto em tracking; calcula se existir registro
            cd = self._cooldowns.get(cand['cpf'])
            cooldown_active = bool(cd and now < cd)
        return {
            'tracking': bool(tracking),
            'progress': float(progress),
            'secondsLeft': float(seconds_left) if seconds_left is not None else None,
            'stableSeconds': float(self.stable_seconds),
            'facesDetected': int(self._last_faces),
            'cooldownActive': bool(cooldown_active)
        }

    def set_timing(self, stable_seconds: Optional[float] = None, cooldown_seconds: Optional[float] = None):
        if stable_seconds is not None:
            try:
                s = float(stable_seconds)
                self.stable_seconds = max(0.5, min(15.0, s))
            except Exception:
                pass
        if cooldown_seconds is not None:
            try:
                c = float(cooldown_seconds)
                self.cooldown_seconds = max(0.0, min(30.0, c))
            except Exception:
                pass

    def pop_last_detection(self) -> Optional[Dict]:
        """Retorna e limpa última detecção para evitar repetidos popups."""
        data = self.last_detection
        self.last_detection = None
        return data

    def consume_detection(self, detection_id: str) -> Optional[Dict]:
        """Consome uma detecção pendente (remove do buffer) e retorna seus dados.
        Retorna dict com chaves: cpf, roi_color (np.ndarray BGR 200x200), best_conf, timestamp, bbox
        """
        return self._pending.pop(detection_id, None)

    # --- Utilidades de diagnóstico/ajuste ---
    def is_trained(self) -> bool:
        with self._lock:
            return self._recognizer is not None

    def get_threshold(self) -> float:
        return float(self.threshold)

    def set_threshold(self, value: float) -> float:
        try:
            v = float(value)
        except Exception:
            return self.threshold
        # Limita dentro de um intervalo razoável para LBPH
        self.threshold = max(30.0, min(150.0, v))
        return self.threshold

    def _detect_faces(self, gray):
        return self._face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=FACE_SIZE)

    def debug_predict(self, frame) -> Dict:
        """Predição para depuração: retorna também quando acima do limiar.
        Escolhe a maior face e roda predict, retornando label, cpf (se houver),
        confiança e se seria reconhecido dado o limiar atual.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._detect_faces(gray)
        if len(faces) == 0:
            return { 'found': False }
        # maior face
        x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
        roi = gray[y:y+h, x:x+w]
        roi = cv2.resize(roi, (200, 200))
        roi = cv2.equalizeHist(roi)
        with self._lock:
            recognizer = self._recognizer
        if recognizer is None:
            return {
                'found': True,
                'trained': False,
                'bbox': [int(x), int(y), int(w), int(h)],
            }
        label_id, confidence = recognizer.predict(roi)
        cpf = self._label_to_cpf.get(label_id)
        recognized = (confidence <= self.threshold) and (cpf is not None)
        return {
            'found': True,
            'trained': True,
            'bbox': [int(x), int(y), int(w), int(h)],
            'label_id': int(label_id),
            'cpf': cpf,
            'confidence': float(confidence),
            'threshold': float(self.threshold),
            'recognized': bool(recognized)
        }


# Instância global (singleton simples)
_service_instance: Optional[FaceRecognitionService] = None

def get_face_service() -> FaceRecognitionService:
    global _service_instance
    if _service_instance is None:
        base = os.path.join(os.path.dirname(__file__), '..', 'constants', 'rostos')
        base = os.path.abspath(base)
        _service_instance = FaceRecognitionService(base)
        _service_instance.train()  # Treino inicial
    return _service_instance
