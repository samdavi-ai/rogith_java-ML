const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const HistoryStore = require('../history-store.js');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'styles.css'), 'utf8');

test('upload is a normal image picker with no camera capture hint', () => {
  const input = html.match(/<input\b[^>]*\bid="imageInput"[^>]*>/)?.[0];
  assert.ok(input, 'image input exists');
  assert.match(input, /accept="image\/jpeg,image\/png"/);
  assert.doesNotMatch(input, /\bcapture(?:\s|=|>)/i);
  assert.match(html, /id="uploadPhotoButton"[^>]*>Upload image</);
  assert.match(app, /\$\('uploadPhotoButton'\)\.addEventListener\('click',[^\n]*imageInput\.click\(\)/);
});

test('live camera remains a separate action with camera lifecycle controls', () => {
  assert.match(html, /id="useCameraButton"[^>]*>Use camera</);
  assert.match(html, /id="startCameraButton"[^>]*>Start camera</);
  assert.match(html, /id="switchCameraButton"/);
  assert.match(html, /id="flashlightButton"/);
  assert.match(html, /id="stopCameraButton"/);
  assert.match(html, /id="captureButton"[^>]*>Capture and identify</);
  assert.match(app, /\$\('useCameraButton'\)\.addEventListener\('click', openCameraPanel\)/);
  assert.match(app, /\$\('startCameraButton'\)\.addEventListener\('click',[\s\S]*?cameraController\.start\(\)/);
});

test('desktop and mobile navigation both expose Identify, Guide, History, and About', () => {
  const nav = html.match(/<nav\b[^>]*id="primaryNavigation"[^>]*>([\s\S]*?)<\/nav>/)?.[1];
  assert.ok(nav, 'primary navigation exists');
  for (const section of ['identify', 'guide', 'history', 'about']) assert.match(nav, new RegExp(`href="#${section}"`));
  assert.match(html, /id="menuToggle"[^>]*aria-expanded="false"[^>]*aria-controls="primaryNavigation"/);
  assert.match(app, /event\.key === 'Escape'[\s\S]*?setNavigationOpen\(false\)/);
  assert.match(app, /if \(link\) setNavigationOpen\(false\)/);
  assert.match(css, /\.site-header nav\.is-open\{display:flex\}/);
});

test('sign-in and login UI or handlers are absent from the frontend', () => {
  assert.doesNotMatch(`${html}\n${app}\n${css}`, /sign\s*in|signin|login/i);
});

test('classification history is saved locally, survives a page reload, and renders in History', () => {
  const values = new Map();
  const storage = {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, value); }
  };
  const record = {name: 'Keyboard', status: 'complete', confidence: 92.4, date: '2026-10-02T10:00:00.000Z'};
  assert.equal(HistoryStore.save(storage, record), true);
  assert.deepEqual(HistoryStore.read(storage), [record]);
  assert.match(html, /id="history"/);
  assert.match(html, /id="historyList"/);
  assert.match(app, /RecoLensHistory\.read\(localStorage\)/);
  assert.match(app, /history-row[\s\S]*?escapeHtml\(name\)/);
  assert.match(app, /Today/);
  assert.match(app, /Yesterday/);
  assert.match(html, /id="clearHistoryButton"[^>]*>Clear history/);
});

test('history storage handles corrupt data, storage failures, and retains only the newest 20 entries', () => {
  const values = new Map([['sc-history', '{bad json']]);
  const storage = {
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, value); }
  };
  assert.deepEqual(HistoryStore.read(storage), []);
  for (let i = 0; i < 22; i++) assert.equal(HistoryStore.save(storage, {name: `Item ${i}`}), true);
  const entries = HistoryStore.read(storage);
  assert.equal(entries.length, 20);
  assert.equal(entries[0].name, 'Item 21');
  assert.equal(entries.at(-1).name, 'Item 2');
  assert.equal(HistoryStore.save({getItem() { return null; }, setItem() { throw new Error('quota'); }}, {name: 'No storage'}), false);
  assert.equal(HistoryStore.clear({removeItem(key) { values.delete(key); }}), true);
  assert.deepEqual(HistoryStore.read(storage), []);
});

test('camera stream only sends a classification after explicit capture', () => {
  const controller = fs.readFileSync(path.join(root,'camera-controller.js'),'utf8');
  assert.match(app, /\$\('captureButton'\)\.addEventListener\('click',[\s\S]*?cameraController\.captureAndClassify\(\)/);
  assert.doesNotMatch(controller, /this\.beginInference\(\);/);
});
