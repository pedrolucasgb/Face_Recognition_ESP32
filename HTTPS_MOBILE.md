# Como usar a câmera no celular (HTTPS necessário)

## Problema

Navegadores mobile (Android/iOS) **exigem HTTPS** para acessar a câmera por segurança.

## Solução: Usar ngrok

O ngrok cria um túnel HTTPS para seu servidor local.

### Passo 1: Instalar ngrok

**Opção A - Windows (via Chocolatey):**
```powershell
choco install ngrok
```

**Opção B - Download manual:**
1. Acesse: https://ngrok.com/download
2. Baixe o executável para Windows
3. Extraia para uma pasta (ex: `C:\ngrok\`)

### Passo 2: Criar conta (grátis)

1. Acesse: https://dashboard.ngrok.com/signup
2. Crie uma conta gratuita
3. Copie seu token de autenticação

### Passo 3: Configurar token

```powershell
ngrok config add-authtoken SEU_TOKEN_AQUI
```

### Passo 4: Iniciar aplicação Flask

```powershell
cd src
python app.py
```

A aplicação estará rodando em: http://localhost:5000

### Passo 5: Criar túnel ngrok

**Em outro terminal:**
```powershell
ngrok http 5000
```

Você verá algo assim:
```
ngrok

Session Status                online
Account                       seu@email.com
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:5000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

### Passo 6: Acessar no celular

**Use a URL HTTPS fornecida pelo ngrok:**
```
https://abc123.ngrok-free.app
```

**Importante:**
- ✅ Use a URL **https://** (não http://)
- ✅ Compartilhe essa URL com qualquer dispositivo na internet
- ⚠️ A URL muda cada vez que você reinicia o ngrok (plano gratuito)
- ⚠️ Plano gratuito tem limite de 40 conexões/minuto

## Alternativa: ngrok pago (URL fixa)

Com plano pago você pode ter:
- URL personalizada que não muda: `https://seuapp.ngrok.app`
- Mais conexões simultâneas
- Melhor performance

```powershell
ngrok http 5000 --domain=seuapp.ngrok.app
```

## Testando

1. Abra a URL do ngrok no celular
2. Permita acesso à câmera quando solicitado
3. A câmera frontal deve aparecer automaticamente
4. Verifique o console do navegador (via debug remoto)

## Debug remoto no celular

### Android (Chrome):
1. No PC: Chrome → chrome://inspect
2. No celular: Configurações → Ativar "Depuração USB"
3. Conecte via USB
4. Veja console do celular no PC

### iOS (Safari):
1. Mac: Safari → Develop → [seu iPhone]
2. iPhone: Ajustes → Safari → Avançado → Web Inspector
3. Veja console do iPhone no Mac

## Solução de problemas

**Erro: "NotAllowedError"**
- Permita acesso à câmera nas configurações do navegador
- Limpe cache e cookies
- Tente em modo anônimo

**Erro: "NotFoundError"**
- Nenhuma câmera detectada
- Verifique se o celular tem câmera funcionando
- Teste com o app de câmera nativo

**Erro: "SecurityError"**
- Certifique-se de usar HTTPS (ngrok)
- Não use HTTP no mobile

**ngrok não funciona:**
- Verifique se configurou o authtoken
- Firewall pode estar bloqueando
- Tente reiniciar o ngrok

## Comandos úteis

```powershell
# Ver configuração do ngrok
ngrok config check

# Ver túneis ativos
ngrok tunnels list

# Parar ngrok
Ctrl+C

# Iniciar com região específica (mais próximo = mais rápido)
ngrok http 5000 --region=sa  # South America
ngrok http 5000 --region=us  # United States
ngrok http 5000 --region=eu  # Europe
```

## Resumo

```
Terminal 1: python app.py
Terminal 2: ngrok http 5000
Celular: Acesse a URL HTTPS fornecida pelo ngrok
```

Pronto! Agora a câmera do celular funcionará perfeitamente. 📱✅
