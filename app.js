const guides = [
  {name:'Phones and tablets',terms:'phone smartphone tablet mobile',desc:'Portable devices often contain lithium batteries and personal data.',prepare:['Back up data, sign out of accounts and reset the device.','Remove SIM and memory cards.','Keep the battery intact; do not puncture or crush it.'],action:'Use an authorized e-waste collection or take-back channel for your area.'},
  {name:'Computers and laptops',terms:'computer laptop desktop pc',desc:'Computers contain reusable components, batteries and storage that may hold personal information.',prepare:['Back up files and securely erase storage where possible.','Remove accessories and any removable media.','Do not dismantle a swollen or damaged battery.'],action:'Take the device to an e-waste collection or recycling channel that accepts computers.'},
  {name:'Batteries and power banks',terms:'battery batteries power bank cell',desc:'Batteries can present a fire risk if damaged, shorted or placed in household waste.',prepare:['Cover exposed terminals with non-conductive tape if safe to do so.','Keep batteries dry and away from heat.','If a battery is swollen, hot or leaking, avoid handling it and seek local hazardous-waste advice.'],action:'Use a battery collection point that explicitly accepts that battery type.'},
  {name:'Displays and televisions',terms:'display monitor tv television screen',desc:'Screens and displays may require separate handling from ordinary household waste.',prepare:['Keep the screen intact and protect it from impact.','Disconnect cables and accessories.'],action:'Check with your local authority or an authorized e-waste channel for display acceptance.'},
  {name:'Light bulbs',terms:'light bulb lamp fluorescent led',desc:'Some bulbs contain materials that require separate handling, and broken bulbs can create a hazard.',prepare:['Keep the bulb intact and protect it from impact.','Do not place a broken bulb in a recycling bin; follow local hazardous-waste instructions.'],action:'Use a collection point that accepts that bulb type and check local handling requirements.'},
  {name:'Circuit boards',terms:'pcb circuit board printed circuit electronics',desc:'Circuit boards contain electronic components and materials that should be handled through an appropriate e-waste channel.',prepare:['Keep the board dry and avoid burning, crushing or dismantling it.','Handle damaged boards carefully and avoid sharp edges.'],action:'Take circuit boards to an authorized electronics recycler or e-waste collection point.'},
  {name:'Printers and peripherals',terms:'printer scanner keyboard mouse',desc:'Printers and peripherals include electronic parts and, in some cases, ink or toner.',prepare:['Remove paper and accessories.','Keep toner or ink cartridges contained and follow their separate return instructions.'],action:'Check that your local e-waste channel accepts printers and peripherals.'},
  {name:'Cables and small electronics',terms:'cable charger adapter router electronics',desc:'Small electronic equipment and cables can contain recoverable materials.',prepare:['Bundle cables without cutting them.','Separate batteries when designed to be safely removable.'],action:'Take them to an e-waste collection point rather than putting them in mixed recycling.'}
];

const $ = id => document.getElementById(id);
const imageInput = $('imageInput'), preview = $('preview'), form = $('identifyForm');
const INFERENCE_INTERVAL_MS = Number(window.EWASTE_CAMERA_CONFIG?.inferenceIntervalMs) || 1000;
const ML_HIGH_CONFIDENCE_THRESHOLD = Number(window.EWASTE_CAMERA_CONFIG?.highConfidenceThreshold) || 0.85;
const ML_MEDIUM_CONFIDENCE_THRESHOLD = Number(window.EWASTE_CAMERA_CONFIG?.mediumConfidenceThreshold) || 0.60;
let selectedFile = null, previewUrl = null, cameraStableUrl = null, stableCameraPrediction = null;

function setError(text = '') { $('uploadError').textContent = text; $('uploadError').hidden = !text; }
function formatBytes(n) { return n < 1024 * 1024 ? `${Math.ceil(n / 1024)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`; }
function clearImage() {
  selectedFile = null;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  imageInput.value = '';
  $('emptyUpload').hidden = false;
  $('previewWrap').hidden = true;
  $('analyzeButton').disabled = true;
  setError('');
}
function selectFile(file) {
  setError('');
  if (!file) return;
  if (!['image/jpeg', 'image/png'].includes(file.type)) { clearImage(); setError('Please choose a JPG or PNG image.'); return; }
  if (file.size > 10 * 1024 * 1024) { clearImage(); setError('This image is larger than 10 MB. Choose a smaller image.'); return; }
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  selectedFile = file;
  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  $('fileName').textContent = file.name;
  $('fileSize').textContent = formatBytes(file.size);
  $('emptyUpload').hidden = true;
  $('previewWrap').hidden = false;
  $('analyzeButton').disabled = false;
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function closeCameraPanel(stop = true) {
  if (stop && cameraController) cameraController.stop('stopped', 'Camera stopped.');
  $('cameraPanel').hidden = true;
  $('cameraSetup').hidden = false;
  $('cameraActive').hidden = true;
  form.hidden = false;
  $('cameraError').hidden = true;
  $('cameraRecovery').hidden = true;
}
function openCameraPanel() {
  $('result').hidden = true;
  $('cameraPanel').hidden = false;
  form.hidden = true;
  if (cameraController.stream) {
    $('cameraSetup').hidden = true;
    $('cameraActive').hidden = false;
    $('cameraPanel').scrollIntoView({behavior:'smooth',block:'start'});
    return;
  }
  $('cameraSetup').hidden = false;
  $('cameraActive').hidden = true;
  $('cameraError').hidden = true;
  $('cameraRecovery').hidden = true;
  $('startCameraButton').disabled = false;
  $('startCameraButton').textContent = 'Start camera';
  $('cameraPanel').scrollIntoView({behavior:'smooth',block:'start'});
}
function handleCameraState(state, message) {
  const start = $('startCameraButton');
  start.disabled = state === 'requesting' || state === 'switching';
  start.textContent = state === 'requesting' ? 'Starting camera…' : 'Start camera';
  if (state === 'active') {
    $('cameraSetup').hidden = true;
    $('cameraSetupMessage').hidden = true;
    $('cameraActive').hidden = false;
    $('cameraError').hidden = true;
    $('cameraRecovery').hidden = true;
    $('cameraLiveMessage').textContent = 'Camera active. Checking a frame for an identification…';
  } else if (state === 'requesting' || state === 'switching') {
    $('cameraError').hidden = true;
    $('cameraRecovery').hidden = true;
    if (state === 'requesting') {
      $('cameraSetupMessage').textContent = message;
      $('cameraSetupMessage').hidden = false;
    }
    $('cameraLiveMessage').textContent = message;
  } else if (['permission-denied','no-camera','in-use','unsupported','error'].includes(state)) {
    $('cameraSetup').hidden = true;
    $('cameraActive').hidden = true;
    $('cameraError').textContent = message;
    $('cameraError').hidden = false;
    $('cameraRecovery').hidden = false;
    $('retryCameraButton').hidden = state === 'no-camera' || state === 'unsupported';
  } else {
    $('cameraSetup').hidden = false;
    $('cameraActive').hidden = true;
    if (message) $('cameraSetupMessage').textContent = message;
    $('cameraSetupMessage').hidden = !message || message === 'Camera stopped.';
  }
}
function renderCameraPrediction(prediction) {
  if (!prediction.stable) {
    if (!stableCameraPrediction) $('cameraLiveMessage').textContent = 'Checking a few frames for a consistent result…';
    return;
  }
  stableCameraPrediction = prediction;
  if (cameraStableUrl) URL.revokeObjectURL(cameraStableUrl);
  cameraStableUrl = URL.createObjectURL(prediction.frame);
  const confidence = prediction.confidence <= 1 ? prediction.confidence : prediction.confidence / 100;
  const percentage = Math.round(confidence * 1000) / 10;
  const level = confidence >= ML_HIGH_CONFIDENCE_THRESHOLD ? 'High confidence' : confidence >= ML_MEDIUM_CONFIDENCE_THRESHOLD ? 'Moderate confidence' : 'Low confidence';
  if (prediction.isUnsure || prediction.category === 'UNSURE' || confidence < ML_MEDIUM_CONFIDENCE_THRESHOLD) {
    $('cameraLiveMessage').textContent = 'Not sure yet. Try moving closer, improving the lighting, or showing the whole item.';
    $('useResultButton').hidden = true;
    $('cameraPrediction').hidden = true;
    return;
  }
  $('cameraLiveMessage').textContent = 'Detected item';
  $('cameraPrediction').innerHTML = `<h4>${escapeHtml(prediction.category)}</h4><p>${percentage}% confidence · ${level}</p>`;
  $('cameraPrediction').hidden = false;
  $('useResultButton').hidden = false;
}

const cameraController = new CameraController({
  video: $('cameraVideo'),
  apiBase: window.EWASTE_API_BASE_URL || '',
  intervalMs: INFERENCE_INTERVAL_MS,
  onState: handleCameraState,
  onCameraCount: count => { $('switchCameraButton').hidden = count < 2; },
  onPrediction: renderCameraPrediction,
  onUnavailable: message => {
    $('cameraLiveMessage').textContent = message;
    $('cameraPrediction').hidden = true;
    $('useResultButton').hidden = true;
    $('retryInferenceButton').hidden = false;
  },
  onNetworkError: message => {
    $('cameraLiveMessage').textContent = message;
    $('retryInferenceButton').hidden = false;
  }
});

$('useCameraButton').addEventListener('click', openCameraPanel);
$('uploadPhotoButton').addEventListener('click', () => { closeCameraPanel(); imageInput.click(); });
$('startCameraButton').addEventListener('click', async () => {
  $('cameraSetupMessage').hidden = true;
  $('cameraError').hidden = true;
  $('cameraRecovery').hidden = true;
  $('cameraPrediction').hidden = true;
  $('useResultButton').hidden = true;
  $('retryInferenceButton').hidden = true;
  stableCameraPrediction = null;
  await cameraController.start();
});
$('retryCameraButton').addEventListener('click', () => cameraController.start());
$('switchCameraButton').addEventListener('click', () => cameraController.switchCamera());
$('stopCameraButton').addEventListener('click', () => {
  cameraController.stop('stopped', 'Camera stopped.');
  $('cameraPrediction').hidden = true;
  $('useResultButton').hidden = true;
  $('retryInferenceButton').hidden = true;
  stableCameraPrediction = null;
});
$('closeCameraButton').addEventListener('click', () => closeCameraPanel());
$('cameraUploadFallback').addEventListener('click', () => { closeCameraPanel(); imageInput.click(); });
$('retryInferenceButton').addEventListener('click', () => {
  $('retryInferenceButton').hidden = true;
  $('cameraPrediction').hidden = true;
  stableCameraPrediction = null;
  cameraController.retryInference();
  $('cameraLiveMessage').textContent = 'Trying the classification service again…';
});
$('useResultButton').addEventListener('click', () => {
  if (!stableCameraPrediction || !cameraStableUrl) return;
  const prediction = stableCameraPrediction;
  cameraController.stop('stopped', 'Camera stopped.');
  $('cameraPanel').hidden = true;
  form.hidden = false;
  $('result').hidden = false;
  renderResult({category:prediction.category,confidence:prediction.confidence,confidenceLevel:prediction.confidenceLevel,alternatives:prediction.alternatives}, $('result'), cameraStableUrl);
  $('result').scrollIntoView({behavior:'smooth',block:'start'});
  stableCameraPrediction = null;
});

const imageInputClick = () => imageInput.click();
$('chooseButton').addEventListener('click', imageInputClick);
$('changeButton').addEventListener('click', imageInputClick);
$('removeButton').addEventListener('click', clearImage);
imageInput.addEventListener('change', event => selectFile(event.target.files[0]));
const drop = $('dropZone');
drop.addEventListener('click', event => { if (!event.target.closest('button')) imageInput.click(); });
drop.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); imageInput.click(); } });
drop.addEventListener('dragover', event => { event.preventDefault(); drop.classList.add('dragging'); });
drop.addEventListener('dragleave', () => drop.classList.remove('dragging'));
drop.addEventListener('drop', event => { event.preventDefault(); drop.classList.remove('dragging'); selectFile(event.dataTransfer.files[0]); });

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!selectedFile) return;
  const button = $('analyzeButton'), result = $('result');
  button.disabled = true;
  button.textContent = 'Analyzing image…';
  setError('');
  result.hidden = false;
  result.innerHTML = '<p class="eyebrow">Identification</p><p>Analyzing image…</p>';
  try {
    const data = new FormData();
    data.append('image', selectedFile);
    const response = await fetch(`${window.EWASTE_API_BASE_URL || ''}/api/classifications`, {method:'POST',body:data});
    const body = await response.json();
    if (!response.ok) throw new Error(body?.error?.message || 'We could not analyze this image. Please try another photo.');
    renderResult(body.data?.classification || body.data || body, result, previewUrl);
  } catch (error) {
    const message = error instanceof TypeError ? 'We couldn’t reach the classification service. Please try again later.' : error.message;
    renderUnavailable(result, message);
  } finally {
    button.disabled = false;
    button.textContent = 'Identify item';
  }
});

function renderUnavailable(target, message) {
  target.innerHTML = `<p class="eyebrow">Identification unavailable</p><p class="result-message error" role="status">${escapeHtml(message)} You can still browse the general guide below.</p><p class="result-disclaimer">Your image was not saved by this page. Try again later or use the general guide.</p>`;
  saveHistory({name:'Analysis unavailable',status:'unavailable',date:new Date().toISOString()});
}
function guideForCategory(category) {
  const normalized = String(category || '').toLowerCase();
  const guideName = normalized.includes('battery') ? 'Batteries and power banks'
    : normalized.includes('phone') ? 'Phones and tablets'
    : normalized.includes('keyboard') || normalized.includes('mouse') ? 'Printers and peripherals'
    : normalized.includes('bulb') ? 'Light bulbs'
    : normalized.includes('circuit') || normalized === 'pcb' || normalized.includes('printed circuit') ? 'Circuit boards' : null;
  const guide = guides.find(item => item.name === guideName);
  return guide ? {recyclingMethod:guide.action, preparationInstructions:guide.prepare, safetyInstructions:guide.desc} : {};
}
function renderResult(item, target, imageSource = previewUrl) {
  const unsure = item.status === 'UNSURE' || item.confidenceLevel === 'UNSURE';
  const name = unsure ? 'Not sure' : item.categoryName || item.category || 'Uncertain identification';
  const conf = Number(item.confidence);
  const pct = Number.isFinite(conf) ? (conf <= 1 ? conf * 100 : conf) : null;
  const confidence = Number.isFinite(pct) ? Math.round(pct * 10) / 10 : null;
  const level = confidence === null ? 'Uncertain' : confidence / 100 >= ML_HIGH_CONFIDENCE_THRESHOLD ? 'High confidence' : confidence / 100 >= ML_MEDIUM_CONFIDENCE_THRESHOLD ? 'Moderate confidence' : 'Low confidence';
  const guidance = item.guide || guideForCategory(name), prepare = guidance.preparationInstructions || guidance.preparation || [], alternatives = unsure ? [] : item.alternatives || [];
  if (unsure) {
    target.innerHTML = `<p class="eyebrow">Identification</p><div class="result-top"><img src="${imageSource || ''}" alt="Selected item photo"><div><p>Estimated match</p><h3>Not sure</h3><span class="confidence">${confidence === null ? 'Uncertain' : `${confidence}% · below the confidence threshold`}</span></div></div><h4>Try another photo</h4><ul><li>Use better lighting.</li><li>Move closer to the item.</li><li>Show the whole item.</li></ul><p class="source-note">The image did not meet the model’s confidence threshold. No category-specific recycling advice is shown.</p><button class="button secondary" id="anotherButton" type="button">Identify another item</button>`;
    target.querySelector('#anotherButton').addEventListener('click', () => { cameraController.stop(); clearImage(); target.hidden = true; if (cameraStableUrl) URL.revokeObjectURL(cameraStableUrl); cameraStableUrl = null; $('identify').scrollIntoView(); });
    saveHistory({name, status:'unsure', confidence, date:new Date().toISOString()});
    return;
  }
  target.innerHTML = `<p class="eyebrow">Identification</p><div class="result-top"><img src="${imageSource || ''}" alt="Selected item photo"><div><p>Estimated match</p><h3>${escapeHtml(name)}</h3><span class="confidence">${confidence === null ? level : `${confidence}% · ${level}`}</span></div></div><h4>What should I do?</h4><p>${escapeHtml(guidance.recyclingMethod || 'Check your local authorized e-waste collection or recycling channel for this item.')}</p>${prepare.length ? `<h4>Before recycling</h4><ul>${prepare.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}<h4>Safety</h4><p>${escapeHtml(guidance.safetyInstructions || 'Do not burn, crush or dismantle batteries. If a battery is swollen, hot or leaking, avoid handling it and seek local hazardous-waste advice.')}</p>${alternatives.length ? `<h4>Possible matches</h4><ul>${alternatives.map(item => `<li>${escapeHtml(item.category || item.name)} — ${Math.round(item.confidence * 100)}%</li>`).join('')}</ul>` : ''}<p class="source-note">${guidance.sourceName ? `Source: ${escapeHtml(guidance.sourceName)} · ` : ''}Guidance varies by location. Identification is based on image analysis and may be uncertain.</p><button class="button secondary" id="anotherButton" type="button">Identify another item</button>`;
  target.querySelector('#anotherButton').addEventListener('click', () => {
    cameraController.stop();
    clearImage();
    target.hidden = true;
    if (cameraStableUrl) URL.revokeObjectURL(cameraStableUrl);
    cameraStableUrl = null;
    $('identify').scrollIntoView();
  });
  saveHistory({name,status:'complete',confidence,date:new Date().toISOString()});
}

function saveHistory(item) {
  let list = JSON.parse(localStorage.getItem('sc-history') || '[]');
  list.unshift(item);
  localStorage.setItem('sc-history', JSON.stringify(list.slice(0,20)));
  renderHistory();
}
function renderHistory() {
  const list = JSON.parse(localStorage.getItem('sc-history') || '[]');
  $('historyList').innerHTML = list.length ? list.map(item => `<div class="history-row"><div class="upload-symbol" aria-hidden="true">${item.status === 'complete' ? '✓' : '?'}</div><div><strong>${escapeHtml(item.name)}</strong><span>${item.status === 'complete' && item.confidence != null ? `${item.confidence}% confidence` : 'No classification saved'}</span></div><time>${new Date(item.date).toLocaleDateString()}</time></div>`).join('') : '<p class="empty-state">You haven’t identified any items yet. Choose a photo above to get started.</p>';
}
function renderGuides(query = '') {
  const matches = guides.filter(guide => (guide.name + ' ' + guide.terms).toLowerCase().includes(query.toLowerCase()));
  $('guideList').innerHTML = matches.length ? matches.map(guide => `<details class="guide-item"><summary>${guide.name}</summary><div class="guide-body"><p>${guide.desc}</p><strong>Before handover</strong><ul>${guide.prepare.map(item => `<li>${item}</li>`).join('')}</ul><p><strong>Recycling:</strong> ${guide.action}</p></div></details>`).join('') : '<p class="empty-state">No matching items found.</p>';
}
$('guideSearch').addEventListener('input', event => renderGuides(event.target.value));
$('accountButton').addEventListener('click', () => alert('Account sign-in is available when the backend authentication service is configured.'));
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden' && cameraController.stream) {
    cameraController.stop('stopped', 'Camera paused because this page is not visible. Start it again when you return.');
    stableCameraPrediction = null;
    $('cameraPrediction').hidden = true;
    $('useResultButton').hidden = true;
  }
});
document.addEventListener('click', event => {
  const link = event.target.closest('a[href^="#"]');
  if (link && link.getAttribute('href') !== '#identify' && cameraController.stream) closeCameraPanel();
});
window.addEventListener('pagehide', () => cameraController.stop());
renderGuides();
renderHistory();
