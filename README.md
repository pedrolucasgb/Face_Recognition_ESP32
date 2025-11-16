# Face_Recognition_ESP32

Sistema de reconhecimento facial para registro de ponto de voluntários do Hospital do Cajuru, com suporte a duas fontes de imagem:

1. Webcam/local (navegador capturando frames via WebRTC)
2. ESP32-CAM (snapshot proxy + stream MJPEG)

O backend usa Flask + OpenCV e um modelo LBPH para reconhecimento. O frontend segue templates unificados e módulos JS compartilhados (reconhecimento e registro).

---
## Sumário
- [Arquitetura Geral](#arquitetura-geral)
- [Templates e Diferenças](#templates-e-diferenças)
- [Rotas HTTP](#rotas-http)
- [Fluxos Principais](#fluxos-principais)
  - [Reconhecimento de Ponto](#reconhecimento-de-ponto)
  - [Cadastro de Rostos](#cadastro-de-rostos)
- [Serviço de Reconhecimento (LBPH + Haar)](#serviço-de-reconhecimento-lbph--haar)
  - [Detecção de Faces (Haar Cascade)](#detecção-de-faces-haar-cascade)
  - [Reconhecimento (LBPH)](#reconhecimento-lbph)
  - [Lógica de Estabilidade e Cooldown](#lógica-de-estabilidade-e-cooldown)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Variáveis de Ambiente / Configuração](#variáveis-de-ambiente--configuração)
- [Captura e Armazenamento de Imagens](#captura-e-armazenamento-de-imagens)
- [Treinamento do Modelo](#treinamento-do-modelo)
- [Endpoints de Diagnóstico e Ajuste](#endpoints-de-diagnóstico-e-ajuste)
- [Expondo com ngrok (proxy reverso)](#expondo-com-ngrok-proxy-reverso)

---
## Arquitetura Geral

```
Browser (Webcam / ESP32 Stream)
   |                
   | frames (base64 jpeg)
   v
Flask Backend (/api/process_frame, /api/process_frame_registro)
   |-- OpenCV: Haar Cascade (detecção)
   |-- OpenCV: LBPHFaceRecognizer (reconhecimento)
   |-- Cache de frames para captura / confirmação
   |-- Armazenamento: src/constants/rostos/<cpf>/imagem.jpg
```

- Reconhecimento em tempo real: cada frame enviado é processado e rotulado; ao atingir estabilidade (tempo parado) é gerada uma detecção pendente para confirmação.
- Cadastro: frames chegam, bounding boxes são desenhados para auxiliar; capturas salvam apenas o rosto recortado (200x200) colorido.

---
## Templates e Diferenças

| Template | Fonte | Propósito | Diferença principal |
|----------|-------|-----------|---------------------|
| `index.html` | Webcam local | Reconhecimento | Uso de `<video>` + canvas hidden de captura; imagem processada em `<img id="processed-frame">` |
| `index_espcam.html` | ESP32-CAM | Reconhecimento | Usa `<img>` do stream e canvas `#overlay` para desenhar o frame processado (sem acessar webcam local) |
| `registro.html` | Webcam local | Cadastro de rosto | Mostra apenas canvas processado (vídeo fica oculto) para exibir bounding boxes claramente |
| `registro_espcam.html` | ESP32-CAM | Cadastro de rosto | Poll de snapshots via `/api/espcam/snapshot`, overlay canvas com bounding box, captura habilitada após primeiro frame processado |

Diferença principal: a origem do frame (webcam vs proxy de snapshot ESP32). O restante (estilos, lógica, componentes) é unificado via CSS único (`app.css`) e módulos JS (`recognition.js`, `registro.js`).

---
## Rotas HTTP

### Páginas
- `GET /` → Página de reconhecimento local (`index.html`)
- `GET /espcam` → Página de reconhecimento via ESP32 (`index_espcam.html`)
- `GET /registro` → Página de cadastro local (`registro.html`)
- `GET /registro_espcam` → Página de cadastro via ESP32 (`registro_espcam.html`)

### Processamento de Frames
- `POST /api/process_frame` → Processa frame para reconhecimento (desenha box, atualiza estado de estabilidade, pode gerar detecção pendente)
  - Body: `{ frame: 'data:image/jpeg;base64,...' }`
  - Return: `{ success, processed_frame, ui }`
- `POST /api/process_frame_registro` → Processa frame para cadastro (desenha bounding box e instruções)
  - Return: `{ success, processed_frame, faces_detected }`

### Detecção / Confirmação
- `GET /api/last_detection` → Retorna e consome última detecção pronta para confirmação (após estabilidade)
  - Return: `{ found: bool, cpf, nome, matricula, horario, confidence, detection_id }`
- `POST /api/confirmar_ponto` → Confirma registro de ponto
  - Body: `{ cpf, confidence?, detection_id? }`
  - Salva recorte do rosto (ROI) ou fallback do frame atual

### Cadastro
- `POST /api/usuario_status` → Verifica se existe (por cpf/matrícula) ou cria novo
  - Return: `{ success, new_user, usuario_id, cpf, message }`
- `POST /api/capturar_foto` → Usa último frame de cadastro e recorta rosto; salva em `rostos/<cpf>`
  - Return: `{ success, count, path }`
- `POST /api/recriar_modelo` → Re-treina LBPH com dataset atual
  - Return: `{ success, message }`

### Listagens / Diagnóstico
- `GET /api/pessoas_registradas` → Lista usuários com contagem de imagens
- `GET /api/pontos_hoje` → Lista pontos registrados no dia
- `GET /api/last_recognition` → Último reconhecimento (não consome)
- `GET /api/model_status` → Status do modelo (threshold, datasets)
- `GET /api/predict_now` → Debug de predição no frame atual

### Ajustes de Parâmetros
- `POST /api/ajustar_limite` → Ajusta threshold LBPH
  - Body: `{ threshold }`
- `POST /api/ajustar_tempos` → Ajusta tempo de estabilidade e cooldown
  - Body: `{ stable_seconds?, cooldown_seconds? }`

### ESP32-CAM Proxy
- `GET /api/espcam/snapshot` → Proxy de snapshot `/capture` evitando CORS

---
## Fluxos Principais

### Reconhecimento de Ponto
1. Cliente captura frame (webcam ou snapshot ESP32) → envia para `/api/process_frame`.
2. Serviço detecta faces, tenta reconhecer com LBPH.
3. Se reconhecido e parado por X segundos (`stable_seconds`) → cria detecção pendente com ROI recortada.
4. Frontend poll `/api/last_detection`; se `found`, abre modal.
5. Usuário confirma → `/api/confirmar_ponto` salva ROI ou recorte do frame atual + registra ponto em tabela `pontos_usuarios`.
6. Cooldown evita popup repetido imediatamente.

### Cadastro de Rostos
1. Usuário verifica/cria pessoa via `/api/usuario_status` (etapa 1 → etapa 2).
2. Frames de cadastro: enviados para `/api/process_frame_registro` (mostra bounding box + instruções).
3. Ao clicar “Capturar Foto” → `/api/capturar_foto` recorta maior face, salva 200x200 BGR.
4. Após fotos suficientes (>=5 mín; ideal 10–15) → “Finalizar” chama `/api/recriar_modelo`.
5. Re-treino LBPH lê todas as pastas `rostos/<cpf>/*.jpg` e recalibra o modelo.

---
## Serviço de Reconhecimento (LBPH + Haar)
Arquivo: `src/services/face_recognition_service.py`

### Detecção de Faces (Haar Cascade)
- Modelo: `haarcascade_frontalface_default.xml` (clássico do OpenCV)
- Técnica baseada em cascatas de classificadores treinados com features Haar e AdaBoost.
- Parâmetros usados:
  - `scaleFactor=1.1` (piramidal, controla redução progressiva)
  - `minNeighbors=5` (filtra falsas detecções exigindo vizinhos)
  - `minSize=(60, 60)` (ignora faces muito pequenas)
- Resultado: bounding boxes (x, y, w, h) para cada face.

### Reconhecimento (LBPH)
- LBPH = Local Binary Patterns Histograms.
- Etapas:
  1. Converte rosto para escala de cinza, redimensiona (200x200), equaliza histograma.
  2. Divide em células (`grid_x`, `grid_y`), extrai padrões binários locais (comparando vizinhos — radius & neighbors).
  3. Constrói histograma concatenado dos padrões.
  4. Treina (para cada label/CPF) armazenando representações.
  5. Predição retorna `label_id` e `confidence` (distância — quanto menor, melhor).
- Parâmetros configurados: `radius=2`, `neighbors=8`, `grid_x=8`, `grid_y=8`.
- Threshold (default 85.0): se `confidence <= threshold` → considerado reconhecido.
- Ajuste possível via endpoint `/api/ajustar_limite`.

### Lógica de Estabilidade e Cooldown
- Objetivo: evitar múltiplos popups e falsos positivos.
- Estados:
  - Candidato ativo: CPF suspeito sendo observado.
  - Tempo parado: precisa ficar `stable_seconds` (default 5s) para confirmar.
  - Cooldown: após detecção confirmada, CPF entra em `cooldown_seconds` (default 5s) e não dispara novamente até expirar.
- Ao completar estabilidade → cria detecção pendente (com ROI colorida) e libera popup no frontend.
- Confirmação consome essa detecção (preserva ROI para salvar imagem do registro de ponto).

---
## Estrutura de Pastas

```
src/
  app.py                # Flask app e rotas
  services/face_recognition_service.py  # Lógica LBPH + detecção
  constants/rostos/<cpf>/...            # Dataset de rostos (fotos capturadas)
  templates/                         # Páginas HTML (unificadas por data-page/data-source)
  static/styles/app.css              # CSS único
  static/js/recognition.js           # Lógica reconhecimento (local + ESP32)
  static/js/registro.js              # Lógica cadastro (local + ESP32)
```

---
## Variáveis de Ambiente / Configuração
Arquivo: `src/constants/config.py`

| Variável | Descrição | Default |
|----------|-----------|---------|
| `ESP32_CAM_ENABLED` | Habilita modo ESP32 | `false` |
| `ESP32_CAM_URL` | URL do stream MJPEG | `http://192.168.1.100:81/stream` |
| `ESP32_SERVER_IP` | IP do servidor que serve proxy | `192.168.1.10` |
| `SESSION_TIMEOUT_SECONDS` | Timeout lógico de sessão | `300` |
| `FRAME_UPLOAD_MAX_SIZE_MB` | Limite de upload (se aplicável) | `5` |
| `CAMERA_MODE` | Estratégia (`client`, `server`, `esp32`, `auto`) | `client` |

---
## Captura e Armazenamento de Imagens

- Cadastro (`/api/capturar_foto`): salva somente o recorte do rosto colorido (200x200) em `src/constants/rostos/<cpf>/cpf_idx_timestamp.jpg`.
- Confirmação de ponto (`/api/confirmar_ponto`): salva ROI colorida `confirm_<timestamp>.jpg` dentro da pasta do CPF.
- Re-treino lê todas as `.jpg` existentes; não diferencia origem (cadastro ou confirmação de ponto).

---
## Treinamento do Modelo

1. Coleta: fotos capturadas por CPF populam pastas.
2. Chamada: `POST /api/recriar_modelo` → `FaceRecognitionService.train()`.
3. Processo: carrega todas imagens, converte para grayscale + equalize, treina LBPH.
4. Resultado: mapeamento `label_id ↔ cpf` atualizado; reconhecedor substituído.
5. Se sem imagens → modelo fica `None` (apenas detecção de faces vermelhas, sem reconhecimento).

---
## Endpoints de Diagnóstico e Ajuste

| Endpoint | Função |
|----------|--------|
| `GET /api/model_status` | Ver status de treinamento e datasets por CPF |
| `GET /api/predict_now` | Predição rápida no frame atual (debug) |
| `POST /api/ajustar_limite` | Ajusta threshold LBPH |
| `POST /api/ajustar_tempos` | Ajusta estabilidade e cooldown |

---
## Expondo com ngrok (proxy reverso)

Para acessar o servidor Flask a partir de dispositivos fora da sua rede local (por exemplo, celulares em 4G ou para uma demonstração remota), usamos um proxy reverso. Existem várias opções (Cloudflare Tunnel, localtunnel, frp etc.), mas neste projeto utilizamos o ngrok pela simplicidade.

Por que ngrok aqui?
- Fornece URL pública HTTPS (importante: navegadores exigem origem segura para liberar permissão de câmera de forma consistente).
- Evita configurar port-forwarding no roteador.
- Permite compartilhar rapidamente o sistema de reconhecimento/cadastro com outros dispositivos.

Passos básicos (Windows PowerShell):

```powershell
# 1) Baixe e instale o ngrok (https://ngrok.com/download)
# 2) Configure seu token (necessário após criar conta):
ngrok config add-authtoken <SEU_AUTHTOKEN>

# 3) Inicie um túnel HTTP para a porta do Flask (default 5000):
ngrok http http://localhost:5000
```

Após iniciar, o ngrok exibirá uma URL pública do tipo:

```
Forwarding  https://<subdomínio>.ngrok.io -> http://localhost:5000
```

Use essa URL pública no celular para acessar o sistema (por exemplo, https://<subdomínio>.ngrok.io/ para reconhecimento e https://<subdomínio>.ngrok.io/registro para cadastro). Como é HTTPS, a permissão de câmera no navegador móvel tende a funcionar melhor.

Notas e limitações com ESP32-CAM:
- O endpoint `/api/espcam/snapshot` faz proxy de uma URL interna do ESP32 (ex.: `http://192.168.1.100/capture`). Ou seja, o servidor Flask precisa enxergar o IP da ESP32 na mesma rede. Se o Flask estiver rodando na sua máquina atrás do ngrok, dispositivos externos verão o site, mas o servidor ainda precisa alcançar a ESP32 via rede local.
- Para cenários fora da LAN, considere colocar o servidor Flask na mesma rede da ESP32 (por exemplo, um PC/NAS local) ou expor a câmera de forma segura (VPN, túnel dedicado) — sempre com cuidado de segurança.

Alternativas ao ngrok:
- Cloudflare Tunnel (gratuito, permite domínio próprio)
- localtunnel (simplicidade, sem conta)
- frp (mais controle, requer um servidor público seu)

Importante: ngrok é ótimo para desenvolvimento/demonstração. Para produção, utilize uma infraestrutura adequada (reverse proxy dedicado, TLS gerenciado, autenticação, proteção de endpoints, WAF etc.).

---
## Conceitos Rápidos dos Dois Modelos

1. **Haar Cascade (Detecção)**:
   - Classificador em cascata treinado com milhares de exemplos de faces e não-faces.
   - Usa features Haar (diferenças de intensidades em regiões retangulares) agregadas por AdaBoost.
   - Muito rápido, mas menos robusto a ângulos e iluminação extremos.

2. **LBPH (Reconhecimento)**:
   - Converte cada rosto para um conjunto de histogramas de padrões binários locais.
   - "Local Binary Pattern": compara pixel central com vizinhos e gera códigos binários.
   - Histogramas capturam textura; método simples e eficiente em datasets pequenos.
   - Confidence é uma distância; valor menor => rosto "mais parecido" com o modelo.

---
## Execução

Instale dependências (Python 3.10+):

```bash
pip install -r requirements.txt
python src/app.py
```

Acesse:
- Local: http://localhost:5000/
- ESP32: http://localhost:5000/espcam (se configurado)

---
## Licença
Projeto interno demonstrativo. Adapte conforme necessidades de compliance e LGPD.

---
## Contato
Dúvidas ou melhorias: abra uma issue ou envie sugestão.
