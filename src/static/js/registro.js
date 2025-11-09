// registro.js - local webcam registration
// Expects body data-page="registro" and data-source="local|espcam"

let usuarioAtualId = null;
let cpfAtual = null;
let fotosCapturadas = 0;
let etapa = 1;
let isProcessing = false;

const body = document.body;
const source = body.dataset.source || 'local';
const isEsp = source === 'espcam';

const video = document.getElementById('video-stream');
const canvas = document.getElementById('canvas');
const ctx = canvas ? canvas.getContext('2d') : null;

function formatCPF(cpf){ return cpf && cpf.length===11 ? cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4') : cpf; }

// CPF mask
const cpfInput = document.getElementById('cpf-pessoa');
cpfInput && cpfInput.addEventListener('input', e => {
  let v = e.target.value.replace(/\D/g,'').slice(0,11);
  v = v.replace(/(\d{3})(\d)/, '$1.$2');
  v = v.replace(/(\d{3})(\d)/, '$1.$2');
  v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
  e.target.value = v;
});

function showMessage(msg, kind){
  const box = document.getElementById('status-messages');
  if(!box) return;
  box.innerHTML='';
  const el=document.createElement('div');
  el.className='status '+(kind==='error'?'error':(kind==='success'?'success':''));
  el.textContent=msg; box.appendChild(el);
  setTimeout(()=>{ if(box.contains(el)) box.removeChild(el); }, 6000);
}

function updateCaptureCounter(){
  const el = document.getElementById('capture-counter');
  if(!el) return;
  el.textContent = `${fotosCapturadas} foto(s) capturada(s).`;
  if(fotosCapturadas>=15){ el.textContent += ' Quantidade ideal atingida.'; }
  else if(fotosCapturadas>=10){ el.textContent += ' Mínimo recomendado atingido.'; }
  // Gate finalize button by minimum photo count
  const btnFinalizar = document.getElementById('btn-finalizar');
  if(btnFinalizar){ btnFinalizar.disabled = fotosCapturadas < 5; }
}

function setLoading(flag){
  const btnVerificar = document.getElementById('btn-verificar');
  if(!btnVerificar) return;
  if(flag){ btnVerificar.textContent='Processando...'; btnVerificar.disabled=true; }
  else { btnVerificar.textContent='Verificar / Continuar'; btnVerificar.disabled=false; }
}

function resetCadastro(){
  if(video && video.srcObject){ video.srcObject.getTracks().forEach(t=>t.stop()); video.srcObject=null; }
  usuarioAtualId=null; cpfAtual=null; fotosCapturadas=0; etapa=1;
  document.getElementById('form-cadastro')?.reset();
  const etapaEl=document.getElementById('etapa'); etapaEl && (etapaEl.textContent='Etapa 1 de 2 — Dados do voluntário');
  document.getElementById('form-panel') && (document.getElementById('form-panel').style.display='block');
  document.getElementById('capture-panel') && (document.getElementById('capture-panel').style.display='none');
  const resetBtn=document.getElementById('btn-reset'); resetBtn && (resetBtn.style.display='none');
  const statusBox=document.getElementById('status-messages'); statusBox && (statusBox.innerHTML='');
  const counter=document.getElementById('capture-counter'); counter && (counter.textContent='Nenhuma foto capturada ainda.');
  // Ensure buttons gated again
  document.getElementById('btn-capturar') && (document.getElementById('btn-capturar').disabled=true);
  document.getElementById('btn-finalizar') && (document.getElementById('btn-finalizar').disabled=true);
}

async function verificarOuCriarUsuario(){
  if(etapa!==1) return;
  const nome = document.getElementById('nome-pessoa').value.trim();
  const cpfFmt = document.getElementById('cpf-pessoa').value.trim();
  const matricula = document.getElementById('matricula-pessoa').value.trim();
  const email = document.getElementById('email-pessoa').value.trim();
  if(!nome||!cpfFmt||!matricula){ showMessage('Preencha nome, CPF e matrícula.', 'error'); return; }
  const cpf = cpfFmt.replace(/\D/g,''); if(cpf.length!==11){ showMessage('CPF inválido.', 'error'); return; }
  try{
    setLoading(true);
    const resp = await fetch('/api/usuario_status',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ nome, cpf, matricula, email })});
    const data = await resp.json();
    if(!data.success){ showMessage(data.message||'Falha na verificação','error'); return; }
    usuarioAtualId=data.usuario_id; cpfAtual=data.cpf; etapa=2;
    const etapaEl=document.getElementById('etapa'); etapaEl && (etapaEl.textContent='Etapa 2 de 2 — Captura de fotos');
    document.getElementById('form-panel').style.display='none';
    document.getElementById('capture-panel').style.display='block';
    // For ESP32, enable capture only after first processed frame; finalize gated by photo count
    if(isEsp){
      document.getElementById('btn-capturar').disabled=true;
    } else {
      document.getElementById('btn-capturar').disabled=false;
    }
    document.getElementById('btn-finalizar').disabled=true; // always start disabled until minimum reached
    document.getElementById('btn-reset').style.display='inline-block';
    showMessage(data.message,'success');
    if(!isEsp){ initCamera(); }
  }catch(err){ showMessage('Erro na comunicação com o servidor','error'); }
  finally{ setLoading(false); }
}

async function capturarFoto(){
  if(!usuarioAtualId){ showMessage('Primeiro conclua etapa 1.', 'error'); return; }
  try{
    const resp = await fetch('/api/capturar_foto',{method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({ usuario_id: usuarioAtualId })});
    const data = await resp.json();
    if(!data.success){ showMessage(data.message||'Erro ao capturar','error'); return; }
    fotosCapturadas=data.count; updateCaptureCounter(); showMessage('Foto salva com sucesso.','success'); loadPessoasRegistradas();
  }catch(err){ showMessage('Erro de comunicação ao capturar','error'); }
}

async function finalizar(){
  if(fotosCapturadas < 5){ showMessage('Capture pelo menos 5 fotos antes de finalizar.', 'error'); return; }
  const overlay = document.getElementById('overlay-training');
  const trainingText = document.getElementById('training-text');
  overlay.classList.remove('hidden'); overlay.setAttribute('aria-hidden','false');
  trainingText.textContent='Iniciando re-treinamento do modelo...';
  const btnFinalizar=document.getElementById('btn-finalizar'); const btnCapturar=document.getElementById('btn-capturar');
  btnFinalizar.disabled=true; btnCapturar.disabled=true;
  showMessage('Recriando modelo com novas imagens...','success');
  try{
    const start=Date.now();
    const resp=await fetch('/api/recriar_modelo',{method:'POST'});
    const data=await resp.json();
    const elapsed=((Date.now()-start)/1000).toFixed(1);
    if(data.success){
      trainingText.textContent=`Modelo atualizado em ${elapsed}s. Redirecionando...`;
      showMessage(data.message||'Modelo atualizado.','success');
      setTimeout(()=>{ window.location.href = isEsp ? "/espcam" : "/"; },1300);
    }
    else { overlay.classList.add('hidden'); overlay.setAttribute('aria-hidden','true'); btnFinalizar.disabled=false; btnCapturar.disabled=false; showMessage(data.message||'Falha ao atualizar modelo.','error'); }
  }catch(err){ overlay.classList.add('hidden'); overlay.setAttribute('aria-hidden','true'); btnFinalizar.disabled=false; btnCapturar.disabled=false; showMessage('Erro ao comunicar com servidor para treinar modelo.','error'); }
}

async function loadPessoasRegistradas(){
  try{
    const response = await fetch('/api/pessoas_registradas');
    const pessoas = await response.json();
    const container = document.getElementById('pessoas-lista');
    if(!container) return;
    if(pessoas.length){
      container.innerHTML = pessoas.map(p => `<div class="pessoa-item"><div><span class="pessoa-nome">${p.nome}</span><br><small class="meta">CPF: ${formatCPF(p.cpf)} | Matrícula: ${p.matricula}</small></div><span class="pessoa-count">${p.imagens} fotos</span></div>`).join('');
    } else { container.innerHTML = '<div class="list-item"><span>Nenhuma pessoa registrada ainda</span></div>'; }
  }catch(err){ const container=document.getElementById('pessoas-lista'); container && (container.innerHTML='<div class="list-item"><span>Erro ao carregar</span></div>'); }
}

// Local camera frame feeding for registro cache
function startFrameProcessingRegistro(){
  if(isEsp) return; // ESP handled elsewhere
  setInterval(async ()=>{
    if(isProcessing || etapa !==2 || !video.videoWidth || !video.videoHeight) return;
    isProcessing = true;
    try{
      // Capture frame from video
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = video.videoWidth;
      tempCanvas.height = video.videoHeight;
      const tempCtx = tempCanvas.getContext('2d');
      tempCtx.drawImage(video, 0, 0);
      const b64 = tempCanvas.toDataURL('image/jpeg', 0.8);
      
      // Send to process and get back with bounding box
      const r = await fetch('/api/process_frame_registro',{method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({ frame: b64 })});
      const data = await r.json();
      
      // Draw processed frame (with bounding box) to visible canvas
      if(data && data.success && data.processed_frame){
        const img = new Image();
        img.onload = () => {
          canvas.width = img.width;
          canvas.height = img.height;
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0);
        };
        img.src = data.processed_frame;
      }
    }catch(e){ /*silent*/ }
    finally{ isProcessing = false; }
  },150);
}

async function initCamera(){
  const statusEl = document.getElementById('camera-status');
  if(statusEl){ statusEl.style.display='block'; statusEl.textContent='Solicitando permissão...'; statusEl.className='camera-status loading'; }
  if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){ statusEl && (statusEl.textContent='✗ Navegador não suporta câmera', statusEl.className='camera-status error'); showMessage('Navegador sem suporte.','error'); return; }
  try{
    const constraints = { video:{ width:{ideal:1280}, height:{ideal:720} }, audio:false };
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream; await video.play();
    statusEl && (statusEl.textContent='✓ Câmera ativa', statusEl.className='camera-status active'); setTimeout(()=>{ if(statusEl) statusEl.style.display='none'; },3000);
    startFrameProcessingRegistro();
  }catch(err){ statusEl && (statusEl.textContent='Erro ao acessar câmera', statusEl.className='camera-status error'); showMessage('Erro ao acessar câmera','error'); }
}

// ESP32 polling for registro (feeding cache)
function startEspPolling(){
  if(!isEsp) return;
  const overlay = document.getElementById('overlay');
  const streamImg = document.getElementById('espcam-stream');
  if(!overlay || !streamImg) return;
  const octx = overlay.getContext('2d');
  function resize(){ const rect=streamImg.getBoundingClientRect(); overlay.width=rect.width; overlay.height=rect.height; overlay.style.width=rect.width+'px'; overlay.style.height=rect.height+'px'; }
  window.addEventListener('resize', resize); streamImg.addEventListener('load', resize);
  let processing=false; let firstFrame=false;
  async function cycle(){
    if(processing || etapa!==2) { setTimeout(cycle,250); return; }
    processing=true;
    try{
      const snap = await fetch('/api/espcam/snapshot?t='+Date.now()); if(!snap.ok) throw new Error('snap');
      const blob = await snap.blob();
      const b64 = await new Promise(res=>{ const fr=new FileReader(); fr.onload=()=>res(fr.result); fr.readAsDataURL(blob); });
      const proc = await fetch('/api/process_frame_registro',{method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({ frame: b64 })});
      const data = await proc.json();
      if(data && data.success && data.processed_frame){
        const img=new Image(); img.onload=()=>{ resize(); octx.clearRect(0,0,overlay.width,overlay.height); octx.drawImage(img,0,0,overlay.width,overlay.height); }; img.src=data.processed_frame;
        if(!firstFrame){ firstFrame=true; const hint=document.getElementById('frame-hint'); hint && (hint.textContent='Frame processado. Captura disponível.'); document.getElementById('btn-capturar').disabled=false; }
      }
    }catch(e){ }
    finally{ processing=false; setTimeout(cycle,250); }
  }
  resize(); setTimeout(cycle,400);
}

function bindEvents(){
  document.getElementById('form-cadastro')?.addEventListener('submit', e=>{ e.preventDefault(); verificarOuCriarUsuario(); });
  document.getElementById('btn-verificar')?.addEventListener('click', verificarOuCriarUsuario);
  document.getElementById('btn-capturar')?.addEventListener('click', capturarFoto);
  document.getElementById('btn-reset')?.addEventListener('click', resetCadastro);
  document.getElementById('btn-finalizar')?.addEventListener('click', finalizar);
}

(function bootstrap(){
  const page = body.dataset.page;
  if(page !== 'registro') return;
  bindEvents();
  loadPessoasRegistradas();
  if(isEsp){ startEspPolling(); } // camera only after etapa 2 for local
})();
