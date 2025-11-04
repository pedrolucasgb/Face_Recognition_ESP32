import cv2
import os
import numpy as np
import time
from datetime import datetime


class FaceRecognizer:
    """Classe responsável pelo reconhecimento facial"""
    
    def __init__(self, data_dir="rostos", confidence_threshold=70.0):
        self.data_dir = data_dir
        self.confidence_threshold = confidence_threshold
        self.face_cascade = None
        self.recognizer = None
        self.nomes = []
        self.setup()
    
    def setup(self):
        """Inicializa o reconhecedor"""
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        if self.face_cascade.empty():
            raise RuntimeError("Erro ao carregar Haar Cascade.")
        
        self.load_and_train()
    
    def carregar_dataset(self):
        """Carrega o dataset de rostos"""
        imagens = []
        labels = []
        nomes = []
        
        if not os.path.exists(self.data_dir):
            raise RuntimeError(f"Diretório '{self.data_dir}' não encontrado.")
        
        nome_para_id = {}
        proximo_id = 0
        
        for nome in sorted(os.listdir(self.data_dir)):
            pasta = os.path.join(self.data_dir, nome)
            if not os.path.isdir(pasta):
                continue
            
            if nome not in nome_para_id:
                nome_para_id[nome] = proximo_id
                nomes.append(nome)
                proximo_id += 1
            
            for arquivo in os.listdir(pasta):
                caminho = os.path.join(pasta, arquivo)
                if not os.path.isfile(caminho):
                    continue
                
                img = cv2.imread(caminho, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                
                img = cv2.resize(img, (200, 200))
                img = cv2.equalizeHist(img)
                
                imagens.append(img)
                labels.append(nome_para_id[nome])
        
        if not imagens:
            raise RuntimeError(
                f"Nenhuma imagem encontrada em '{self.data_dir}'. "
                "Estrutura esperada: rostos/NOME/arquivo.jpg"
            )
        
        return imagens, np.array(labels, dtype=np.int32), nomes
    
    def load_and_train(self):
        """Carrega o dataset e treina o reconhecedor"""
        print(f"Carregando dataset em '{self.data_dir}'...")
        imagens, labels, nomes = self.carregar_dataset()
        self.nomes = nomes
        print(f"Pessoas detectadas: {', '.join(nomes)}")
        
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=2,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )
        self.recognizer.train(imagens, labels)
        print("Reconhecedor treinado com sucesso!")
    
    def detect_faces(self, frame, min_size=(80, 80)):
        """Detecta rostos no frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=min_size
        )
        
        return faces, gray
    
    def recognize_face(self, gray_frame, face_coords):
        """Reconhece um rosto específico"""
        x, y, w, h = face_coords
        
        # Recorta o rosto
        roi_gray = gray_frame[y:y+h, x:x+w]
        roi_gray = cv2.resize(roi_gray, (200, 200))
        roi_gray = cv2.equalizeHist(roi_gray)
        
        # Predição
        label_id, confidence = self.recognizer.predict(roi_gray)
        
        if confidence <= self.confidence_threshold:
            nome = self.nomes[label_id]
            return nome, confidence
        
        return None, confidence
    
    def get_registered_names(self):
        """Retorna lista de nomes cadastrados"""
        return self.nomes.copy()


class FaceDetector:
    """Classe responsável apenas pela detecção de rostos (para registro)"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        if self.face_cascade.empty():
            raise RuntimeError("Erro ao carregar Haar Cascade para detecção.")
    
    def detect_faces(self, frame, min_size=(80, 80)):
        """Detecta rostos no frame"""
        faces = self.face_cascade.detectMultiScale(
            frame,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=min_size
        )
        
        return faces


class FaceRegistration:
    """Classe responsável pelo registro de novos rostos"""
    
    def __init__(self, data_dir="rostos"):
        self.data_dir = data_dir
        self.detector = FaceDetector()
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Garante que o diretório de dados existe"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def create_person_folder(self, nome):
        """Cria pasta para uma pessoa"""
        pasta = os.path.join(self.data_dir, nome)
        if not os.path.exists(pasta):
            os.makedirs(pasta)
            return True, f"Pasta criada para {nome}"
        else:
            return False, f"Pasta já existe para {nome}"
    
    def save_face_image(self, frame, nome, face_coords=None):
        """Salva uma imagem de rosto"""
        pasta = os.path.join(self.data_dir, nome)
        
        if not os.path.exists(pasta):
            os.makedirs(pasta)
        
        if face_coords is not None:
            x, y, w, h = face_coords
            # Recorta o rosto
            rosto = frame[y:y+h, x:x+w]
            # Redimensiona para tamanho padrão
            rosto = cv2.resize(rosto, (200, 200))
        else:
            rosto = frame
        
        # Conta imagens existentes
        existing_files = [f for f in os.listdir(pasta) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        next_number = len(existing_files) + 1
        
        # Salva a imagem
        filename = f"{nome}_{next_number:03d}.jpg"
        filepath = os.path.join(pasta, filename)
        
        success = cv2.imwrite(filepath, rosto)
        
        if success:
            return True, filepath, len(existing_files) + 1
        else:
            return False, None, 0
    
    def get_person_image_count(self, nome):
        """Retorna o número de imagens de uma pessoa"""
        pasta = os.path.join(self.data_dir, nome)
        if not os.path.exists(pasta):
            return 0
        
        files = [f for f in os.listdir(pasta) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        return len(files)
    
    def list_registered_people(self):
        """Lista pessoas já registradas"""
        if not os.path.exists(self.data_dir):
            return []
        
        pessoas = []
        for nome in os.listdir(self.data_dir):
            pasta = os.path.join(self.data_dir, nome)
            if os.path.isdir(pasta):
                count = self.get_person_image_count(nome)
                pessoas.append({"nome": nome, "imagens": count})
        
        return sorted(pessoas, key=lambda x: x["nome"])