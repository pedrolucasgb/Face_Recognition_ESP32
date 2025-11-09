# Sistema de Reconhecimento Facial - Guia de Uso

## 🚀 Iniciar o Servidor

```bash
cd "c:\Users\PEDRO GRU\estudos\Face_Recognition_ESP32"
python src/app.py
```

O servidor estará disponível em: **http://localhost:5000**

## 📱 Acessar do Celular/Tablet

1. Conecte o dispositivo na **mesma rede Wi-Fi** que o computador
2. Descubra o IP do servidor (será exibido no console ao iniciar)
3. Acesse no navegador do dispositivo: `http://192.168.X.X:5000`
4. Permita acesso à câmera quando solicitado

## 📋 Fluxo de Uso

### 1️⃣ Cadastrar Novo Voluntário

1. Acesse: **http://localhost:5000/registro**
2. Digite o CPF (apenas números)
3. Clique em **"Verificar CPF"**
4. Se novo usuário:
   - Preencha: Nome, Matrícula, E-mail
   - Clique em **"Salvar cadastro"**
5. Posicione o rosto centralizado na câmera
6. Clique em **"Capturar foto"** várias vezes (recomendado: 15-20 fotos)
   - Varie ângulos: frente, leve inclinação esquerda/direita
   - Varie expressões: neutro, sorrindo, sério
   - Mantenha boa iluminação frontal
7. Clique em **"Finalizar cadastro"**
8. Aguarde treinamento do modelo (pode levar alguns segundos)
9. Será redirecionado para tela de reconhecimento

### 2️⃣ Registrar Ponto (Reconhecimento Facial)

1. Acesse: **http://localhost:5000**
2. Permita acesso à câmera
3. Posicione seu rosto centralizado (50-70cm de distância)
4. Aguarde detecção automática (~5 segundos)
5. Modal de confirmação abrirá com seus dados:
   - Nome
   - CPF
   - Matrícula
   - Horário
   - Confiança do reconhecimento
6. Confira os dados e clique em **"Confirmar"**
7. Ponto registrado com sucesso!

## 🎥 Requisitos de Câmera

### Navegadores Compatíveis
- ✅ Chrome/Edge (recomendado)
- ✅ Firefox
- ✅ Safari (iOS/macOS)
- ✅ Samsung Internet (Android)

### Permissões
- Permita acesso à câmera quando solicitado
- Se negado acidentalmente:
  - Chrome: Clique no **ícone de cadeado** → Permissões → Câmera → Permitir
  - Firefox: Clique no **ícone de escudo** → Permissões → Câmera → Permitir

### Dicas de Iluminação
- ✅ Luz frontal (janela ou luminária à frente)
- ❌ Evite luz forte atrás (contraluz)
- ✅ Ambiente bem iluminado
- ❌ Evite sombras fortes no rosto

## 🔧 Configuração ESP32-CAM (Opcional)

### Requisitos
- ESP32-CAM configurado com stream MJPEG
- Mesma rede Wi-Fi que o servidor

### Configuração
1. Edite `.env` (crie se não existir):
   ```env
   ESP32_CAM_ENABLED=true
   ESP32_CAM_URL=http://192.168.1.100:81/stream
   ESP32_SERVER_IP=192.168.1.10
   ```

2. Altere os valores:
   - `ESP32_CAM_URL`: URL do stream da ESP32-CAM
   - `ESP32_SERVER_IP`: IP que ativa a ESP32 automaticamente

3. Reinicie o servidor

### Teste ESP32
```bash
python test_multicliente.py
```

## ⚙️ Ajustes de Reconhecimento

### Threshold (Limiar de Confiança)
- Padrão: **85**
- Menor = mais rigoroso (menos falsos positivos)
- Maior = mais permissivo (pode aceitar rostos parecidos)

Para ajustar via API:
```bash
curl -X POST http://localhost:5000/api/ajustar_limite -H "Content-Type: application/json" -d "{\"threshold\": 75}"
```

### Tempos de Estabilidade
- **Estabilidade**: 5s (tempo para confirmar reconhecimento)
- **Cooldown**: 5s (intervalo mínimo entre registros do mesmo CPF)

Para ajustar via API:
```bash
curl -X POST http://localhost:5000/api/ajustar_tempos -H "Content-Type: application/json" -d "{\"estabilidade\": 3, \"cooldown\": 10}"
```

## 🐛 Solução de Problemas

### Câmera não detectada
- ✅ Verifique se há outra aba/app usando a câmera
- ✅ Feche outros programas (Zoom, Teams, Skype)
- ✅ Recarregue a página (F5)
- ✅ Verifique permissões do navegador

### Não reconhece meu rosto
- ✅ Capture mais fotos no cadastro (15-20)
- ✅ Varie ângulos e expressões
- ✅ Melhore a iluminação
- ✅ Ajuste o threshold (diminua para ser mais rigoroso)
- ✅ Refaça o cadastro: `/api/recriar_modelo` (POST)

### Frame travado/lento
- ✅ Verifique conexão de internet (se acessando remotamente)
- ✅ Reduza qualidade da câmera (edite `ideal: 1280` para `640` nos templates)
- ✅ Feche outras abas/programas pesados

### Servidor não inicia
```bash
# Verifique Python instalado
python --version

# Instale dependências
pip install -r requirements.txt

# Verifique porta em uso
netstat -ano | findstr :5000
```

## 📊 Banco de Dados

### Localização
`c:\Users\PEDRO GRU\estudos\Face_Recognition_ESP32\src\constants\database.db`

### Tabelas
- **usuario**: CPF, Nome, Matrícula, Email, foto_path, ativo
- **ponto_usuario**: usuario_id, data_hora, confiança, foto_registro_path, dispositivo

### Consultar pontos registrados hoje
```bash
curl http://localhost:5000/api/pontos_hoje
```

### Listar pessoas cadastradas
```bash
curl http://localhost:5000/api/pessoas_registradas
```

## 📁 Estrutura de Arquivos

```
Face_Recognition_ESP32/
├── src/
│   ├── app.py                    # Aplicação principal
│   ├── constants/
│   │   ├── config.py            # Configurações
│   │   └── rostos/              # Fotos de treinamento
│   │       └── <cpf>/           # Uma pasta por CPF
│   │           └── *.jpg        # Fotos (200x200 px, cor)
│   ├── services/
│   │   ├── face_recognition_service.py  # LBPH + detecção
│   │   ├── session_manager.py   # Gerenciador de sessões
│   │   └── esp32_client.py      # Cliente ESP32-CAM
│   ├── templates/
│   │   ├── index_client.html    # Tela de reconhecimento
│   │   └── registro_client.html # Tela de cadastro
│   └── models/
│       ├── db.py                # Configuração BD
│       └── models.py            # Modelos SQLAlchemy
├── test_multicliente.py         # Testes automáticos
├── ARQUITETURA_MULTICLIENTE.md  # Documentação técnica
└── README_USO.md               # Este arquivo
```

## 🔐 Segurança

⚠️ **Este sistema está em desenvolvimento e NÃO deve ser exposto à internet pública**

Recomendações:
- Use apenas em rede local (LAN)
- Configure firewall adequadamente
- Implemente autenticação antes de produção
- Use HTTPS em produção (certificado SSL)

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique os logs do servidor (console onde executou `python src/app.py`)
2. Consulte `ARQUITETURA_MULTICLIENTE.md` para detalhes técnicos
3. Execute testes: `python test_multicliente.py`
