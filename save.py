import cv2
import os

def main(device_index=0, nome_pasta="Mauricio", num_imagens=100):
    # Cria a pasta se não existir
    if not os.path.exists(nome_pasta):
        os.makedirs(nome_pasta)
        print(f"Pasta '{nome_pasta}' criada.")
    else:
        print(f"Pasta '{nome_pasta}' já existe.")

    # Carrega o classificador de rosto do OpenCV
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print("Erro: não foi possível abrir a webcam.")
        return

    contador = 0
    print("Capturando rostos... pressione 'q' para sair antes do fim.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Falha ao capturar frame.")
            break

        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(frame, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in faces:
            # Desenha bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Recorta o rosto detectado
            rosto = frame[y:y+h, x:x+w]

            # Redimensiona para tamanho fixo (ex: 200x200)
            rosto = cv2.resize(rosto, (200, 200))

            # Salva a imagem
            contador += 1
            caminho_arquivo = os.path.join(nome_pasta, f"{nome_pasta}_{contador}.jpg")
            cv2.imwrite(caminho_arquivo, rosto)
            print(f"Imagem {contador} salva em {caminho_arquivo}")

        # Mostra o vídeo
        cv2.imshow("Captura de Rostos - Pressione 'q' para sair", frame)

        # Sai manualmente com 'q' ou automaticamente após 100 imagens
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if contador >= num_imagens:
            print(f"Captura concluída ({num_imagens} imagens salvas).")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Finalizado.")

if __name__ == "__main__":
    main()
