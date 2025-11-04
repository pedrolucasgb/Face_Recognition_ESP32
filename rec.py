import cv2
import os
import numpy as np

# ---------- Configurações ----------
DATA_DIR = "rostos"            # Estrutura: rostos/<NOME>/*.jpg
DEVICE_INDEX = 0               # Índice da câmera
MIN_FACE_SIZE = (80, 80)       # Ignore rostos muito pequenos
LBPH_RADIUS = 2
LBPH_NEIGHBORS = 8
LBPH_GRID_X = 8
LBPH_GRID_Y = 8
# Para LBPH, quanto MENOR, melhor. Ajuste conforme seu dataset:
CONFIDENCE_THRESHOLD = 70.0    # típico entre ~45 e ~90
# -----------------------------------

def carregar_dataset(data_dir):
    imagens = []
    labels = []
    nomes = []

    # Mapeia nome -> id numérico
    nome_para_id = {}
    proximo_id = 0

    for nome in sorted(os.listdir(data_dir)):
        pasta = os.path.join(data_dir, nome)
        if not os.path.isdir(pasta):
            continue

        # Atribui id ao nome
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
            # Normaliza tamanho (opcional; ajuda a estabilidade)
            img = cv2.resize(img, (200, 200))
            # Equaliza contrastes para LBPH
            img = cv2.equalizeHist(img)

            imagens.append(img)
            labels.append(nome_para_id[nome])

    if not imagens:
        raise RuntimeError(
            f"Nenhuma imagem encontrada em '{data_dir}'. "
            "Estrutura esperada: rostos/NOME/arquivo.jpg"
        )

    return imagens, np.array(labels, dtype=np.int32), nomes

def treinar_reconhecedor(imagens, labels):
    # LBPH precisa do pacote opencv-contrib
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=LBPH_RADIUS,
        neighbors=LBPH_NEIGHBORS,
        grid_x=LBPH_GRID_X,
        grid_y=LBPH_GRID_Y
    )
    recognizer.train(imagens, labels)
    return recognizer

def main():
    # Carrega classificador de detecção de rosto
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if face_cascade.empty():
        print("Erro ao carregar Haar Cascade.")
        return

    # Carrega dataset e treina
    print(f"Carregando dataset em '{DATA_DIR}'...")
    imagens, labels, nomes = carregar_dataset(DATA_DIR)
    print(f"Pessoas detectadas: {', '.join(nomes)}")
    recognizer = treinar_reconhecedor(imagens, labels)
    print("Reconhecedor treinado. Abrindo webcam... (pressione 'q' para sair)")

    cap = cv2.VideoCapture(DEVICE_INDEX)
    if not cap.isOpened():
        print("Erro: não foi possível abrir a webcam.")
        return

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Falha ao capturar frame.")
                break

            # Converte para cinza para detecção/reconhecimento
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=MIN_FACE_SIZE
            )

            for (x, y, w, h) in faces:
                # Recorta o rosto e prepara para o reconhecedor
                roi_gray = gray[y:y+h, x:x+w]
                roi_gray = cv2.resize(roi_gray, (200, 200))
                roi_gray = cv2.equalizeHist(roi_gray)

                # Predição
                label_id, confidence = recognizer.predict(roi_gray)
                # Para LBPH: quanto menor confidence, melhor o match
                if confidence <= CONFIDENCE_THRESHOLD:
                    nome = nomes[label_id]
                    # Desenha bounding box e o nome dentro (ou logo acima) da caixa
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

                    # Posição do texto: dentro da caixa, no topo
                    text = f"{nome} {confidence:.1f}"
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    text_x = x + 5
                    text_y = max(y + th + 5, y + 25)
                    cv2.rectangle(frame, (x, y), (x + tw + 10, y + th + 10), (0, 255, 0), -1)
                    cv2.putText(frame, text, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                else:
                    # Não mostra nada se não reconhecer bem (atende “se não for Pedro, não mostre nada”)
                    # Simplesmente ignore este rosto.
                    pass

            cv2.imshow("Reconhecimento de Rostos (LBPH)", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
