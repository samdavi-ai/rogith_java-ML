const fs = require('node:fs');
const path = require('node:path');

const apiBase = process.env.EWASTE_API_BASE_URL;
if (!apiBase) throw new Error('Set EWASTE_API_BASE_URL to the deployed HTTPS API origin.');
const parsed = new URL(apiBase);
if (parsed.protocol !== 'https:') throw new Error('EWASTE_API_BASE_URL must use HTTPS for deployed sites.');

const root = path.resolve(__dirname, '..');
const output = path.join(root, 'frontend-dist');
fs.rmSync(output, {recursive: true, force: true});
fs.mkdirSync(output, {recursive: true});
for (const file of ['index.html', 'styles.css', 'app.js', 'camera-controller.js']) {
  fs.copyFileSync(path.join(root, file), path.join(output, file));
}
fs.writeFileSync(path.join(output, 'api-config.js'),
  `window.EWASTE_API_BASE_URL = ${JSON.stringify(parsed.origin)};\n`);
console.log(`Built frontend for ${parsed.origin}`);
