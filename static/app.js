// ── State ──────────────────────────────────────────────────────────────────
const S = {
  demoMode: true,
  file: null,
  result: null,
  lat: 19.076, lon: 72.877,
  address: '',
  totalCredits: 0,
  dashMap: null,
  miniMap: null,
};

// ── Severity helpers ───────────────────────────────────────────────────────
const SEV_COLOR = { Low:'#22c55e', Medium:'#f59e0b', High:'#f97316', Critical:'#ef4444' };
const SEV_BG    = { Low:'rgba(34,197,94,.12)', Medium:'rgba(245,158,11,.12)', High:'rgba(249,115,22,.12)', Critical:'rgba(239,68,68,.12)' };
const sc = l => SEV_COLOR[l] || '#f59e0b';
const sb = l => SEV_BG[l]    || 'rgba(245,158,11,.12)';

// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.add('active');
  document.querySelector(`[data-tab="${name}"]`).classList.add('active');
  if (name === 'complaint') buildComplaint();
  if (name === 'dashboard') loadDashboard();
}
document.querySelectorAll('.nav-btn').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));

// ── Demo toggle ────────────────────────────────────────────────────────────
document.getElementById('demo-toggle').addEventListener('change', e => S.demoMode = e.target.checked);

// ── File upload + drag & drop ──────────────────────────────────────────────
const zone   = document.getElementById('upload-zone');
const fInput = document.getElementById('file-input');
const prev   = document.getElementById('preview');
const ph     = document.getElementById('upload-placeholder');
const rmBtn  = document.getElementById('remove-btn');
const anBtn  = document.getElementById('analyze-btn');

zone.addEventListener('click', e => { if (e.target !== rmBtn) fInput.click(); });
fInput.addEventListener('change', e => { if (e.target.files[0]) setFile(e.target.files[0]); });

zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', ()  => zone.classList.remove('drag-over'));
zone.addEventListener('drop', e => {
  e.preventDefault(); zone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f?.type.startsWith('image/')) setFile(f);
});

function setFile(f) {
  S.file = f;
  prev.src = URL.createObjectURL(f);
  prev.hidden = false; ph.hidden = true; rmBtn.hidden = false;
  anBtn.disabled = false;
}

rmBtn.addEventListener('click', e => {
  e.stopPropagation();
  S.file = null; prev.src = ''; prev.hidden = true;
  ph.hidden = false; rmBtn.hidden = true;
  anBtn.disabled = true; fInput.value = '';
});

// ── Camera ─────────────────────────────────────────────────────────────────
let stream = null;
const camModal  = document.getElementById('cam-modal');
const camVideo  = document.getElementById('cam-video');
const camCanvas = document.getElementById('cam-canvas');

document.getElementById('camera-btn').addEventListener('click', async () => {
  camModal.hidden = false;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video:{ facingMode:'environment' } });
    camVideo.srcObject = stream;
  } catch {
    alert('Camera not available — please upload a photo instead.');
    camModal.hidden = true;
  }
});

function closeCamera() {
  camModal.hidden = true;
  stream?.getTracks().forEach(t => t.stop());
  stream = null;
}
document.getElementById('cam-close').addEventListener('click', closeCamera);
document.getElementById('cam-cancel').addEventListener('click', closeCamera);

document.getElementById('cam-capture').addEventListener('click', () => {
  camCanvas.width  = camVideo.videoWidth;
  camCanvas.height = camVideo.videoHeight;
  camCanvas.getContext('2d').drawImage(camVideo, 0, 0);
  camCanvas.toBlob(blob => {
    setFile(new File([blob], 'capture.jpg', { type:'image/jpeg' }));
    closeCamera();
  }, 'image/jpeg', 0.92);
});

// ── GPS ────────────────────────────────────────────────────────────────────
document.getElementById('gps-btn').addEventListener('click', () => {
  if (!navigator.geolocation) return alert('Geolocation not supported.');
  navigator.geolocation.getCurrentPosition(pos => {
    S.lat = pos.coords.latitude;
    S.lon = pos.coords.longitude;
    document.getElementById('lat').value = S.lat.toFixed(4);
    document.getElementById('lon').value = S.lon.toFixed(4);
  }, () => alert('Could not get GPS. Enter coordinates manually.'));
});
document.getElementById('lat').addEventListener('change', e => S.lat = parseFloat(e.target.value));
document.getElementById('lon').addEventListener('change', e => S.lon = parseFloat(e.target.value));
document.getElementById('address').addEventListener('input', e => S.address = e.target.value);

// ── Analyze ────────────────────────────────────────────────────────────────
anBtn.addEventListener('click', async () => {
  if (!S.file) return;
  const btnText = document.getElementById('btn-text');
  const spin    = document.getElementById('btn-spin');
  btnText.textContent = 'Analyzing…'; spin.hidden = false; anBtn.disabled = true;

  const form = new FormData();
  form.append('image', S.file);
  form.append('demo_mode', S.demoMode ? 'true' : 'false');
  form.append('lat', S.lat); form.append('lon', S.lon);

  try {
    const res  = await fetch('/api/analyze', { method:'POST', body:form });
    const data = await res.json();
    S.result = data;
    renderResult(data);
  } catch (err) {
    alert('Analysis error: ' + err.message);
  } finally {
    btnText.textContent = 'Analyze with AI'; spin.hidden = true; anBtn.disabled = false;
  }
});

// ── Render result ──────────────────────────────────────────────────────────
function renderResult(d) {
  document.getElementById('empty-result').hidden = true;
  const card = document.getElementById('result-card');
  card.hidden = false;

  if (!d.waste_detected) {
    const isError = !!d.error;
    const msg = d.description || 'The AI did not detect illegal waste in this image. Try a clearer photo from a closer angle showing the dump.';
    card.innerHTML = `
      <div class="res-head"><span style="color:${isError?'#ef4444':'#f59e0b'};font-weight:700">${isError ? 'Analysis Error' : 'No Dumping Detected'}</span></div>
      <div class="desc-block">${msg}</div>
      ${isError ? `<div class="desc-block" style="font-size:11px;color:var(--t3);margin-top:6px">Technical detail: ${d.error}</div>` : ''}`;
    return;
  }

  const color = sc(d.severity_label);
  const bg    = sb(d.severity_label);
  const pct   = d.severity * 10;
  const qc    = d.image_quality === 'Good' ? '#22c55e' : '#f59e0b';

  card.innerHTML = `
    ${d.duplicate ? `<div class="dup-warn">⚠ Possible duplicate — nearby report <strong>${d.duplicate.ticket_id}</strong> already exists. Consider upvoting that ticket.</div>` : ''}

    <div class="res-head">
      <div>
        <div style="font-size:12px;color:var(--t2);margin-bottom:4px">Severity Score</div>
        <div class="sev-score" style="color:${color}">${d.severity}<span style="font-size:16px;color:var(--t2);font-weight:500">/10</span></div>
        <div class="sev-sub">${d.severity_label} severity level</div>
      </div>
      <span class="sev-badge" style="background:${bg};color:${color}">${d.severity_label}</span>
    </div>

    <div class="meter-wrap">
      <div class="meter-track"><div class="meter-fill" id="sev-fill" style="width:0;background:${color}"></div></div>
    </div>

    <div class="res-row"><span class="rl">Waste Type</span><span class="rv" style="text-transform:capitalize">${d.waste_type}</span></div>
    <div class="res-row"><span class="rl">Health Risk</span><span class="rv" style="color:${d.health_risk==='High'?'var(--crit)':d.health_risk==='Medium'?'var(--med)':'var(--low)'}">${d.health_risk}</span></div>
    <div class="res-row"><span class="rl">Volume</span><span class="rv">${d.estimated_volume}</span></div>
    <div class="res-row"><span class="rl">Estimated Weight</span><span class="rv">${(d.estimated_weight_kg||0).toLocaleString()} kg</span></div>
    <div class="res-row"><span class="rl">Image Quality</span><span class="quality-pill" style="background:${qc}20;color:${qc}">${d.image_quality}</span></div>

    <div class="desc-block">${d.description}</div>

    <div class="action-block">
      <div class="action-lbl">Recommended Action</div>
      ${d.recommended_action}
    </div>

    ${d.civic_credits ? `<div class="credits-block"><span class="credits-lbl">★ Civic Credits Earned</span><span class="credits-val">+${d.civic_credits}</span></div>` : ''}

    <div id="mini-map" class="map-sm"></div>

    <div class="proceed-row">
      <button class="btn-primary" onclick="switchTab('complaint')">Generate Complaint →</button>
    </div>
  `;

  // Animate severity bar
  setTimeout(() => { document.getElementById('sev-fill').style.width = pct + '%'; }, 80);

  // Mini map
  setTimeout(() => {
    if (S.miniMap) { S.miniMap.remove(); S.miniMap = null; }
    S.miniMap = L.map('mini-map', { zoomControl:false, attributionControl:false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(S.miniMap);
    S.miniMap.setView([S.lat, S.lon], 15);
    L.circleMarker([S.lat, S.lon], { radius:12, color, weight:2, fillColor:color, fillOpacity:.25 })
      .addTo(S.miniMap).bindPopup(`${d.waste_type} · severity ${d.severity}/10`);
  }, 200);
}

// ── Build complaint ────────────────────────────────────────────────────────
function buildComplaint() {
  const empty   = document.getElementById('complaint-empty');
  const content = document.getElementById('complaint-content');

  if (!S.result?.waste_detected) {
    empty.hidden = false; content.hidden = true; return;
  }
  empty.hidden = true; content.hidden = false;

  const r   = S.result;
  const now = new Date().toLocaleString('en-GB', { dateStyle:'long', timeStyle:'short' });

  document.getElementById('complaint-text').value =
`To the Environmental Complaints Department,

I am writing to formally report an illegal waste dumping incident that requires immediate attention.

INCIDENT DETAILS
════════════════════════════════════════
Date / Time   : ${now}
Location      : ${S.address || 'See GPS coordinates below'}
GPS           : ${S.lat.toFixed(6)}, ${S.lon.toFixed(6)}
Waste Type    : ${(r.waste_type||'').replace(/^\w/,c=>c.toUpperCase())}
Severity      : ${r.severity} / 10  (${r.severity_label})
Volume        : ${r.estimated_volume}
Est. Weight   : ${(r.estimated_weight_kg||0).toLocaleString()} kg
Health Risk   : ${r.health_risk}

DESCRIPTION
════════════════════════════════════════
${r.description}

RECOMMENDED ACTION
════════════════════════════════════════
${r.recommended_action}

Photographic evidence and GPS coordinates are attached.
I kindly request prompt action and an acknowledgment of receipt.

Submitted via DumpAlert Autonomous Reporting System
Powered by Gemini Vision AI · Open311 GeoReport v2 / Swachhata-MoHUA`;

  // Summary card
  const color = sc(r.severity_label);
  const bg    = sb(r.severity_label);
  document.getElementById('complaint-summary').innerHTML = `
    <div class="card-body">
      <div class="field-label">Report Summary</div>
      <div style="background:${bg};border:1px solid ${color}50;border-radius:var(--rs);padding:14px;margin-bottom:14px">
        <div style="font-size:30px;font-weight:900;color:${color};line-height:1">${r.severity_label}</div>
        <div style="font-size:12px;color:var(--t2);margin-top:3px">Severity · ${r.severity}/10</div>
      </div>
      <div class="res-row"><span class="rl">Waste Type</span><span class="rv" style="text-transform:capitalize">${r.waste_type}</span></div>
      <div class="res-row"><span class="rl">Health Risk</span><span class="rv">${r.health_risk}</span></div>
      <div class="res-row"><span class="rl">Est. Weight</span><span class="rv">${(r.estimated_weight_kg||0).toLocaleString()} kg</span></div>
      <div class="res-row"><span class="rl">Civic Credits</span><span class="rv" style="color:var(--pri)">+${r.civic_credits||0}</span></div>
    </div>`;
}

// ── File report ────────────────────────────────────────────────────────────
document.getElementById('file-btn').addEventListener('click', async () => {
  const btnText = document.getElementById('file-btn-text');
  const spin    = document.getElementById('file-spin');
  const fileBtn = document.getElementById('file-btn');
  btnText.textContent = 'Filing…'; spin.hidden = false; fileBtn.disabled = true;

  const platform = document.querySelector('input[name="platform"]:checked').value;

  try {
    const res  = await fetch('/api/file-report', {
      method:'POST',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify({ ...S.result, lat:S.lat, lon:S.lon, address:S.address, platform })
    });
    const data = await res.json();
    S.totalCredits += S.result.civic_credits || 0;
    document.getElementById('total-credits').textContent = S.totalCredits;
    showTicket(data);
    updateSidebarStats();
  } catch (err) {
    alert('Filing failed: ' + err.message);
  } finally {
    btnText.textContent = 'File Report'; spin.hidden = true; fileBtn.disabled = false;
  }
});

function showTicket(d) {
  const card = document.getElementById('ticket-card');
  card.hidden = false;
  card.innerHTML = `
    <div class="tk-lbl">Report Successfully Filed</div>
    <div class="tk-id">${d.ticket_id}</div>
    <div class="tk-status"><span class="tk-dot" style="background:var(--low)"></span> Open — Pending Review</div>
    <div class="tk-meta">
      Platform: <strong>${d.platform}</strong><br>
      Category: <strong>${d.category?.name}</strong> (ID: ${d.category?.id})<br>
      Swachhata Code: <strong>${d.category?.swachhata_code}</strong>
    </div>
    <button class="copy-btn" onclick="navigator.clipboard.writeText('${d.ticket_id}').then(()=>this.textContent='Copied ✓').catch(()=>{})">Copy Ticket ID</button>`;
}

// ── Dashboard ──────────────────────────────────────────────────────────────
async function loadDashboard() {
  const reports = await fetch('/api/reports').then(r => r.json()).catch(() => []);
  const empty   = document.getElementById('dash-empty');
  const content = document.getElementById('dash-content');

  if (!reports.length) { empty.hidden = false; content.hidden = true; return; }
  empty.hidden = true; content.hidden = false;

  const total   = reports.length;
  const open    = reports.filter(r => r.status === 'Open').length;
  const crit    = reports.filter(r => r.severity >= 7).length;
  const avgSev  = (reports.reduce((s,r) => s+r.severity, 0) / total).toFixed(1);
  const credits = reports.reduce((s,r) => s+(r.civic_credits||0), 0);

  document.getElementById('metrics').innerHTML =
    metric('Total Reports', total, '') +
    metric('Open', open, 'Awaiting action') +
    metric('High / Critical', crit, 'Severity ≥ 7') +
    metric('Avg Severity', avgSev+'/10', '') +
    metric('Credits Awarded', credits, 'Civic Credits');

  // Map
  if (!S.dashMap) {
    const clat = reports.reduce((s,r) => s+r.lat,0) / total;
    const clon = reports.reduce((s,r) => s+r.lon,0) / total;
    S.dashMap = L.map('dash-map');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution:'© OpenStreetMap' }).addTo(S.dashMap);
    S.dashMap.setView([clat, clon], 12);
  }
  reports.forEach(r => {
    const c = sc(r.severity_label);
    L.circleMarker([r.lat, r.lon], { radius:13, color:c, weight:2, fillColor:c, fillOpacity:.22 })
      .addTo(S.dashMap)
      .bindPopup(`<b>${r.ticket_id}</b><br>${r.waste_type} · ${r.severity}/10<br>${r.status}`);
  });

  // List
  document.getElementById('report-list').innerHTML = [...reports].reverse().map(r => {
    const c  = sc(r.severity_label);
    const sc2 = r.status==='Resolved' ? 'var(--low)' : r.status==='In Progress' ? '#60a5fa' : '#f59e0b';
    return `
      <div class="report-row">
        <div class="r-dot" style="background:${c}"></div>
        <div class="r-info">
          <div class="r-id">${r.ticket_id}</div>
          <div class="r-meta">${r.waste_type} · ${(r.estimated_weight_kg||0).toLocaleString()} kg · ${r.timestamp}</div>
        </div>
        <span class="status-pill" style="background:${sc2}20;color:${sc2}">${r.status}</span>
      </div>`;
  }).join('');

  updateSidebarStats();
}

function metric(label, value, sub) {
  return `<div class="metric">
    <div class="m-lbl">${label}</div>
    <div class="m-val">${value}</div>
    ${sub ? `<div class="m-sub">${sub}</div>` : ''}
  </div>`;
}

async function updateSidebarStats() {
  const reports = await fetch('/api/reports').then(r => r.json()).catch(() => []);
  document.getElementById('sb-total').textContent = reports.length;
  document.getElementById('sb-open').textContent  = reports.filter(r=>r.status==='Open').length;
  document.getElementById('sb-crit').textContent  = reports.filter(r=>r.severity>=8).length;
}
