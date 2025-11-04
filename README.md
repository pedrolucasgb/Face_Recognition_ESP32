# 🎭 Sistema de Reconhecimento Facial - Controle de Ponto

Sistema completo de reconhecimento facial com interface web usando Flask para controle automático de ponto.

## 📋 Funcionalidades

- ✅ **Reconhecimento Facial em Tempo Real**: Identifica pessoas cadastradas automaticamente
- ⏰ **Registro Automático de Ponto**: Registra horário quando uma pessoa é reconhecida
- 🌐 **Interface Web Moderna**: Dashboard em tempo real com stream da webcam
- 📊 **Estatísticas**: Acompanhamento de pontos do dia e pessoas presentes
- 🔄 **Cooldown Inteligente**: Evita registros duplicados (30 segundos entre registros)
- 📱 **Design Responsivo**: Interface adaptável para desktop e mobile

## 🚀 Como Usar

### 1. Instalação das Dependências

```bash
pip install -r requirements.txt
```

### 2. Estrutura de Dados

Certifique-se de ter a pasta `rostos/` com subpastas para cada pessoa:
```
rostos/
├── Pedro/
│   ├── pedro_1.jpg
│   ├── pedro_2.jpg
│   └── ...
├── Lari/
│   ├── lari_1.jpg
│   └── ...
└── ...
```

### 3. Capturar Fotos (Opcional)

Para adicionar uma nova pessoa, use o script `save.py`:
```bash
python save.py
```

### 4. Executar o Sistema Web

```bash
python app.py
```

Acesse: `http://localhost:5000`

## 🖥️ Interface Web

A interface web inclui:

### 📹 **Stream da Webcam**
- Exibe feed da câmera em tempo real
- Mostra bounding boxes ao detectar rostos
- Verde: pessoa reconhecida | Vermelho: desconhecido

### 📊 **Dashboard em Tempo Real**
- **Status Atual**: Horário e último reconhecimento
- **Pessoas Cadastradas**: Lista de todas as pessoas no sistema
- **Pontos de Hoje**: Registro de todos os pontos do dia
- **Estatísticas**: Métricas do dia atual

### ⚡ **Funcionalidades Automáticas**
- **Registro de Ponto**: Automático quando pessoa é reconhecida
- **Cooldown**: 30 segundos entre registros da mesma pessoa
- **Log Persistente**: Todos os pontos salvos em `pontos_registrados.json`

## 📁 Estrutura do Projeto

```
Face_Recognition_ESP32/
├── app.py                      # Aplicação Flask principal
├── face.py                     # Script original de detecção
├── rec.py                      # Script original de reconhecimento
├── save.py                     # Script para capturar fotos
├── requirements.txt            # Dependências Python
├── pyproject.toml             # Configuração do projeto
├── pontos_registrados.json    # Log de pontos (gerado automaticamente)
├── templates/
│   └── index.html             # Interface web
└── rostos/                    # Dataset de fotos
    ├── Pedro/
    ├── Lari/
    ├── Mauricio/
    └── Pati/
```

## ⚙️ Configurações

No arquivo `app.py`, você pode ajustar:

```python
# Configurações principais
DATA_DIR = "rostos"              # Pasta das fotos
DEVICE_INDEX = 0                 # Índice da câmera
CONFIDENCE_THRESHOLD = 70.0      # Limite de confiança (menor = mais restritivo)
MIN_FACE_SIZE = (80, 80)        # Tamanho mínimo do rosto para detecção
```

## 🔧 Scripts Individuais

### `face.py` - Detecção Básica
Detecta rostos sem reconhecimento:
```bash
python face.py
```

### `rec.py` - Reconhecimento via OpenCV
Reconhecimento facial usando LBPH:
```bash
python rec.py
```

### `save.py` - Captura de Fotos
Captura fotos para treinamento:
```bash
python save.py
```

## 📊 Arquivo de Pontos

Os pontos são salvos em `pontos_registrados.json`:
```json
[
  {
    "nome": "Pedro",
    "horario": "2025-11-04 14:30:25",
    "data": "2025-11-04",
    "hora": "14:30:25"
  }
]
```

## 🚨 Solucionando Problemas

### Câmera não funciona
- Verifique se a câmera não está sendo usada por outro aplicativo
- Tente alterar `DEVICE_INDEX` para 1, 2, etc.

### Reconhecimento impreciso
- Ajuste `CONFIDENCE_THRESHOLD` (valores menores = mais restritivo)
- Adicione mais fotos de treinamento para a pessoa

### Erro ao carregar modelo
- Certifique-se de ter instalado `opencv-contrib-python`
- Verifique se a pasta `rostos/` existe e tem fotos

## 🌟 Próximas Funcionalidades

- 📈 Relatórios semanais/mensais
- 🔔 Notificações em tempo real
- 👤 Cadastro via interface web
- 📧 Envio de relatórios por email
- 🎯 Integração com sistemas de RH

## 📄 Licença

Este projeto está sob a licença MIT.
