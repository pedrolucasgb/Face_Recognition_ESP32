import cv2

def main(device_index=0):
    # Carrega o classificador pré-treinado de rosto (vem com o OpenCV)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if face_cascade.empty():
        print("Erro: não foi possível carregar o classificador de rostos.")
        return

    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print(f"Erro: não foi possível abrir a câmera {device_index}.")
        return

    print("Pressione 'q' para sair.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Falha ao capturar frame.")
                break

            # Converte para cinza (detecção é mais rápida/estável em grayscale)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detecta rostos
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,   # quão rápido reduz a escala da imagem
                minNeighbors=5,    # quão robusta é a validação de um rosto
                minSize=(60, 60)   # ignora detecções muito pequenas
            )

            # Desenha bounding boxes
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Exibe
            cv2.imshow("Webcam - Face Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main(device_index=0)  # troque para 1, 2... se tiver mais câmeras
