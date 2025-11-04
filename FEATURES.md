# Sistema de Reconhecimento Facial - Flask App

## ✨ Principais Melhorias Implementadas

### 🔄 **Sistema de 3 Segundos para Registro**
- **Reconhecimento Contínuo**: A pessoa deve ser reconhecida por 3 segundos consecutivos para registrar o ponto
- **Barra de Progresso**: Mostra visualmente o progresso do reconhecimento na tela da câmera
- **Cooldown Inteligente**: 30 segundos entre registros da mesma pessoa para evitar duplicatas
- **Sessões de Reconhecimento**: Sistema gerencia múltiplas sessões simultâneas

### 📁 **Código Modularizado**
- **modules/face_recognition.py**: Reconhecimento facial, detecção e registro
- **modules/ponto_manager.py**: Gerenciamento de pontos e sessões
- **modules/camera_manager.py**: Controle de câmera e processamento de frames
- **app.py**: Aplicação Flask principal (muito mais limpa)

### 🌐 **Tela de Registro de Pessoas**
- **Interface Intuitiva**: Página dedicada para registro de novas pessoas
- **Stream de Vídeo Específico**: Camera view otimizada para captura
- **Feedback Visual**: Instruções claras e status em tempo real
- **Contagem de Fotos**: Acompanha quantas fotos foram capturadas
- **Validação de Rostos**: Garante que apenas um rosto seja detectado por vez

## 🚀 Como Executar

### 1. Instalar Dependências
```bash
pip install flask opencv-contrib-python numpy
```

### 2. Executar o Sistema
```bash
python app.py
```

### 3. Acessar as Interfaces
- **Sistema Principal**: http://localhost:5000
- **Registro de Pessoas**: http://localhost:5000/registro

## 📱 Funcionalidades da Interface

### **Página Principal** (`/`)
- ✅ Stream da câmera com reconhecimento em tempo real
- ✅ Barra de progresso de 3 segundos para cada pessoa
- ✅ Status de reconhecimento e último ponto registrado
- ✅ Lista de pessoas cadastradas
- ✅ Pontos registrados no dia
- ✅ Estatísticas em tempo real

### **Página de Registro** (`/registro`)
- ✅ Stream da câmera otimizado para captura
- ✅ Campo para nome da pessoa
- ✅ Botão para criar pasta da pessoa
- ✅ Botão para capturar fotos (múltiplas)
- ✅ Contador de fotos capturadas
- ✅ Lista de pessoas já registradas
- ✅ Instruções claras de uso

## 🔧 APIs Disponíveis

- `GET /api/pessoas` - Lista pessoas cadastradas
- `GET /api/pontos_hoje` - Pontos do dia atual
- `GET /api/statistics` - Estatísticas completas
- `GET /api/last_recognition` - Último reconhecimento
- `GET /api/pessoas_registradas` - Pessoas com contagem de imagens
- `POST /api/registrar_pessoa` - Criar nova pasta para pessoa
- `POST /api/capturar_foto` - Capturar foto da câmera

## 🎯 Fluxo de Funcionamento

### **Para Reconhecimento (3 segundos)**:
1. Sistema detecta rosto na câmera
2. Reconhece a pessoa (se cadastrada)
3. Inicia contador de 3 segundos
4. Mostra barra de progresso na tela
5. Se pessoa permanecer por 3 segundos → registra ponto
6. Se pessoa sair antes → reinicia contador
7. Cooldown de 30 segundos após registro

### **Para Registro de Nova Pessoa**:
1. Acessa `/registro`
2. Digite nome da pessoa
3. Clica "Criar Pasta"
4. Posiciona pessoa na câmera (1 rosto apenas)
5. Clica "Capturar Foto" múltiplas vezes
6. Recomendado: 10-15 fotos em ângulos diferentes
7. Sistema automaticamente treina com novas imagens

## 🛠️ Estrutura de Arquivos Atualizada

```
Face_Recognition_ESP32/
├── app.py                      # Flask app principal (modular)
├── modules/                    # Módulos do sistema
│   ├── __init__.py
│   ├── face_recognition.py     # Reconhecimento e registro
│   ├── ponto_manager.py        # Controle de pontos
│   └── camera_manager.py       # Gerenciamento de câmera
├── templates/
│   ├── index.html             # Interface principal
│   └── registro.html          # Interface de registro
├── rostos/                    # Dataset (gerado automaticamente)
├── pontos_registrados.json    # Log de pontos
├── requirements.txt
└── README.md
```

## 🎨 Recursos Visuais

- **Bounding Boxes Coloridas**:
  - 🟢 Verde: Pessoa reconhecida
  - 🔵 Azul: Em processo de reconhecimento  
  - 🔴 Vermelho: Desconhecido

- **Barras de Progresso**: Mostram tempo restante para registro
- **Informações na Tela**: Timestamp, último reconhecimento, instruções
- **Interface Responsiva**: Funciona em desktop e mobile
- **Feedback em Tempo Real**: Status e mensagens instantâneas

## 🔒 Recursos de Segurança

- **Validação de Entrada**: Nomes obrigatórios e válidos
- **Detecção de Múltiplos Rostos**: Impede captura com várias pessoas
- **Cooldown System**: Previne registros duplicados
- **Error Handling**: Tratamento robusto de erros de câmera e arquivo

Este sistema agora está completamente modular, com interface profissional e sistema de 3 segundos implementado!