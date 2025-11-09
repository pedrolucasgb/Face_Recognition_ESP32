// recognition.js - unified recognition logic for local webcam and ESP32-CAM
// Usage: add data-page="recognition" and data-source="local|espcam" to <body>
// Requires:
//  - local: #video-stream, #canvas (hidden capture), optional #processed-frame
//  - espcam: #raw-stream (img), #overlay (canvas)

const body = document.body;
const source = body.dataset.source || 'local';
const isEsp = source === 'espcam';

const stabWrap = document.getElementById('stability-wrap');
const stabFill = document.getElementById('stability-fill');
const stabText = document.getElementById('stability-text');

let processing = false;

function updateStability(ui){
  if(!ui){ stabWrap && (stabWrap.style.display = 'none'); return; }
  if(ui.tracking){
    stabWrap && (stabWrap.style.display = 'block');
    const pct = Math.max(0, Math.min(1, ui.progress || 0));
    stabFill && (stabFill.style.width = (pct*100).toFixed(0)+'%');
    const secs = (ui.secondsLeft != null) ? ui.secondsLeft.toFixed(1) : '';
    stabText && (stabText.textContent = secs ? `Mantenha-se parado por ${secs}s` : 'Mantenha-se parado...');
  } else {
    stabWrap && (stabWrap.style.display = 'none');
    stabFill && (stabFill.style.width = '0%');
  }
}

// Modal polling (common)
(function setupModalPolling(){
  const modal = document.getElementById('confirm-modal');
  const mNome = document.getElementById('m-nome');
  const mCpf = document.getElementById('m-cpf');
  const mMat = document.getElementById('m-mat');
  const mHora = document.getElementById('m-hora');
  const mConf = document.getElementById('m-conf');
  const mStatus = document.getElementById('m-status');
  let detCache = null;
  if(!modal) return;

  function openModal(det){
    if(!modal) return;
    mNome.textContent = det.nome;
    mCpf.textContent = det.cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    mMat.textContent = det.matricula;
    mHora.textContent = new Date(det.horario).toLocaleString('pt-BR');
    mConf.textContent = det.confidence != null ? `(confiança: ${det.confidence.toFixed(1)})` : '';
    mStatus.textContent = '';
    modal.style.display = 'flex';
  }
  function closeModal(){ if(modal){ modal.style.display='none'; } detCache = null; }

  async function pollDetection(){
    try{ const r = await fetch('/api/last_detection'); const data = await r.json(); if(data && data.found){ detCache=data; openModal(data);} }catch(e){/*silent*/}
  }
  setInterval(pollDetection, 1200);

  const btnCancel = document.getElementById('btn-cancelar');
  const btnConfirm = document.getElementById('btn-confirmar');
  btnCancel && (btnCancel.onclick = closeModal);
  btnConfirm && (btnConfirm.onclick = async function(){
    if(!detCache) return;
    try{
      mStatus.textContent = 'Registrando...';
      btnConfirm.disabled = true; btnCancel.disabled = true;
      const r = await fetch('/api/confirmar_ponto', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ cpf: detCache.cpf, confidence: detCache.confidence, detection_id: detCache.detection_id })});
      if(!r.ok){ const text = await r.text(); mStatus.textContent = `Falha (${r.status}). ${text || 'Resposta inválida do servidor.'}`; btnConfirm.disabled=false; btnCancel.disabled=false; return; }
      let resp; try{ resp = await r.json(); }catch{ mStatus.textContent='Resposta inválida (JSON).'; btnConfirm.disabled=false; btnCancel.disabled=false; return; }
      if(resp && resp.success){ mStatus.textContent='Ponto registrado com sucesso!'; setTimeout(closeModal, 1000); }
      else { mStatus.textContent=(resp&&resp.message)?resp.message:'Falha ao registrar ponto.'; btnConfirm.disabled=false; btnCancel.disabled=false; }
    }catch(err){ mStatus.textContent='Problema de conexão ao enviar dados.'; btnConfirm.disabled=false; btnCancel.disabled=false; }
  });
})();

async function runLocal(){
  const video = document.getElementById('video-stream');
  const canvas = document.getElementById('canvas');
  if(!video || !canvas) return;
  const ctx = canvas.getContext('2d');
  const statusEl = document.getElementById('camera-status');

  // init camera
  async function init(){
    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
      statusEl && (statusEl.textContent='✗ Navegador não suporta câmera', statusEl.className='camera-status error');
      return;
    }
    try{
      statusEl && (statusEl.textContent='Solicitando permissão...', statusEl.className='camera-status loading');
      const constraints = { video: { width:{ideal:1280}, height:{ideal:720} }, audio:false };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      video.srcObject = stream; await video.play();
      statusEl && (statusEl.textContent='✓ Câmera ativa', statusEl.className='camera-status active');
      setTimeout(()=>{ if(statusEl) statusEl.style.display='none'; }, 3000);
    }catch(err){ statusEl && (statusEl.textContent=`Erro: ${err.name}`, statusEl.className='camera-status error'); }
  }

  async function cycle(){
    if(processing || !video.videoWidth || !video.videoHeight) return;
    processing = true;
    try{
      canvas.width = video.videoWidth; canvas.height = video.videoHeight; ctx.drawImage(video,0,0);
      const b64 = canvas.toDataURL('image/jpeg', 0.8);
      const resp = await fetch('/api/process_frame', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ frame: b64 }) });
      const data = await resp.json();
      updateStability(data.ui);
      const processed = document.getElementById('processed-frame');
      if(processed && data.processed_frame){ processed.src = data.processed_frame; }
    }catch(e){ /*silent*/ }
    finally{ processing=false; }
  }

  await init();
  setInterval(cycle, 100);
}

async function runEsp(){
  const raw = document.getElementById('raw-stream');
  const overlay = document.getElementById('overlay');
  if(!raw || !overlay) return;
  const ctx = overlay.getContext('2d');
  function resize(){ const rect = raw.getBoundingClientRect(); overlay.width=rect.width; overlay.height=rect.height; overlay.style.width=rect.width+'px'; overlay.style.height=rect.height+'px'; }
  window.addEventListener('resize', resize); raw.addEventListener('load', resize);

  async function cycle(){
    if(processing) return; processing = true;
    try{
      const snap = await fetch('/api/espcam/snapshot?t='+Date.now()); if(!snap.ok) throw new Error('snapshot');
      const blob = await snap.blob();
      const b64 = await new Promise(res=>{ const fr = new FileReader(); fr.onload=()=>res(fr.result); fr.readAsDataURL(blob); });
      const pr = await fetch('/api/process_frame', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ frame: b64 }) });
      const data = await pr.json();
      updateStability(data.ui);
      if(data && data.processed_frame){
        const img = new Image(); img.onload = ()=>{ resize(); ctx.clearRect(0,0,overlay.width,overlay.height); ctx.drawImage(img,0,0,overlay.width,overlay.height); }; img.src = data.processed_frame;
      }
    }catch(e){ /*silent*/ }
    finally{ processing=false; setTimeout(cycle, 200); }
  }

  resize(); setTimeout(cycle, 400);
}

(function bootstrap(){
  const page = body.dataset.page;
  if(page !== 'recognition') return;
  if(isEsp){ runEsp(); } else { runLocal(); }
})();
