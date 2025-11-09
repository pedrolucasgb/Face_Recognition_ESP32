# Câmera Dinâmica - Documentação

## Alterações Implementadas

O sistema foi modificado para usar **câmera dinâmica** em vez de streaming estático do servidor.

### Como funciona agora:

#### 1. **Dispositivo Móvel (Celular/Tablet)**
- Usa câmera **frontal** (`facingMode: 'user'`)
- Ideal para selfies e reconhecimento facial

#### 2. **Desktop/Laptop**
- Usa **webcam padrão** (`facingMode: 'environment'`)
- Detecta automaticamente a câmera disponível

### Mudanças Técnicas:

#### Backend (`app.py`):
- ✅ Removido: `get_camera()` e funções de streaming estático
- ✅ Criado: `/api/process_frame` - processa frames para reconhecimento
- ✅ Criado: `/api/process_frame_registro` - processa frames para cadastro
- ✅ Os frames são enviados via POST em base64
- ✅ Servidor processa e retorna frame com anotações

#### Frontend (`index.html` e `registro.html`):
- ✅ Substituído `<img>` por `<video>` + `<canvas>`
- ✅ JavaScript detecta tipo de dispositivo automaticamente
- ✅ Captura frames da câmera local (~10 fps)
- ✅ Envia frames via POST para processamento
- ✅ Vídeo espelhado para melhor UX (`transform: scaleX(-1)`)

### Benefícios:

1. **Privacidade**: Câmera não fica ativa no servidor
2. **Flexibilidade**: Cada dispositivo usa sua própria câmera
3. **Mobile-First**: Câmera frontal em celulares automaticamente
4. **Compatibilidade**: Funciona em qualquer navegador moderno
5. **Sem latência**: Processamento local + servidor remoto

### Permissões Necessárias:

O navegador solicitará permissão para acessar a câmera na primeira vez.
Certifique-se de:
- ✅ Permitir acesso à câmera quando solicitado
- ✅ Usar HTTPS em produção (obrigatório para getUserMedia)
- ✅ Verificar configurações de privacidade do navegador

### Fluxo de Dados:

```
Dispositivo (Browser)           Servidor Flask
      |                              |
      | 1. getUserMedia()            |
      | (acessa câmera local)        |
      |                              |
      | 2. Captura frame (canvas)    |
      |                              |
      | 3. POST /api/process_frame   |
      |---------------------------->|
      |    (base64 JPEG)            | 4. Decodifica
      |                             | 5. Reconhece faces
      |                             | 6. Desenha retângulos
      | 7. Retorna frame processado |
      |<----------------------------|
      |    (base64 JPEG)            |
      |                              |
      | 8. Atualiza display          |
      | (opcional)                   |
```

### Compatibilidade:

- ✅ Chrome/Edge (desktop e mobile)
- ✅ Firefox (desktop e mobile)
- ✅ Safari (iOS 11+)
- ⚠️ Requer HTTPS em produção
- ⚠️ HTTP funciona apenas em localhost para desenvolvimento

### Troubleshooting:

**Câmera não aparece:**
1. Abra `test_camera.html` no navegador para diagnóstico detalhado
2. Verifique permissões do navegador (ícone de câmera na barra de endereço)
3. Certifique-se que está usando HTTPS ou localhost
4. Verifique se a câmera não está em uso por outro app
5. Tente em modo anônimo/privado do navegador
6. Verifique o console do navegador (F12) para erros específicos

**Erros comuns:**
- `NotAllowedError`: Você negou a permissão - permita nas configurações
- `NotFoundError`: Nenhuma câmera detectada - conecte uma câmera
- `NotReadableError`: Câmera em uso - feche outros aplicativos
- `SecurityError`: Use HTTPS em produção (HTTP funciona apenas em localhost)

**Performance lenta:**
- Ajuste FPS no código (atualmente ~10fps para reconhecimento, ~7fps para registro)
- Reduza qualidade JPEG (atualmente 0.8)
- Reduza resolução da câmera

**Câmera errada:**
- Mobile sempre tenta usar frontal
- Desktop usa padrão do sistema
- Para mudar: modifique `facingMode` no código

### Como testar:

1. **Desktop (Laptop/PC):**
   ```powershell
   cd src
   python app.py
   ```
   Acesse: http://localhost:5000
   ✅ Funciona com HTTP em localhost

2. **Mobile (Celular/Tablet):**
   ⚠️ **HTTPS OBRIGATÓRIO** para câmera no mobile!
   
   Use **ngrok** para criar um túnel HTTPS:
   ```powershell
   # Terminal 1
   cd src
   python app.py
   
   # Terminal 2
   ngrok http 5000
   ```
   
   Acesse a URL HTTPS fornecida pelo ngrok no celular.
   
   📖 **Ver guia completo:** `HTTPS_MOBILE.md`

3. **Console do navegador:**
   - Pressione F12
   - Vá na aba "Console"
   - Você verá mensagens como "Câmeras disponíveis" e "Câmera inicializada com sucesso"
