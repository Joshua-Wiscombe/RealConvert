'use strict';

/* ======================================================================
   RealConvert — browser UI
   ====================================================================== */

const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const ICONS = {
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  folder: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>',
  gear: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  retry: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  alert: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
  film: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  list: '<path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M8 6h13"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  sliders: '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
  phone: '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
};
const icon = (name, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`;

const VIDEO_FORMATS = [
  { id: 'mp4', label: 'MP4', note: 'Plays everywhere' },
  { id: 'mov', label: 'MOV', note: 'Apple & Final Cut' },
  { id: 'mkv', label: 'MKV', note: 'Exact original streams' },
  { id: 'webm', label: 'WEBM', note: 'Open web format' },
];
const AUDIO_FORMATS = [
  { id: 'mp3', label: 'MP3', note: 'Plays everywhere' },
  { id: 'wav', label: 'WAV', note: 'Uncompressed, for editing' },
  { id: 'm4a', label: 'M4A', note: 'AAC, Apple-friendly' },
  { id: 'flac', label: 'FLAC', note: 'Lossless' },
  { id: 'opus', label: 'OPUS', note: 'Small & efficient' },
  { id: 'original', label: 'Original', note: 'No conversion at all' },
];
const BITRATES = ['320', '256', '192', '128'];
const RUNGS = [2160, 1440, 1080, 720, 480, 360];
const BROWSER_NAMES = {
  chrome: 'Chrome', edge: 'Microsoft Edge', firefox: 'Firefox', brave: 'Brave', opera: 'Opera',
  vivaldi: 'Vivaldi', chromium: 'Chromium', safari: 'Safari',
};

function qualityTag(v) {
  if (v >= 4320) return '8K';
  if (v >= 2160) return '4K';
  if (v >= 1440) return '2K';
  if (v >= 1080) return 'Full HD';
  if (v >= 720) return 'HD';
  return '';
}

/* ---------------- preferences (remembered in this browser) ---------------- */

const PREF_KEY = 'realconvert-prefs';
const prefs = Object.assign(
  { mode: 'video', videoFormat: 'mp4', audioFormat: 'mp3', audioQuality: '320', compat: true },
  (() => { try { return JSON.parse(localStorage.getItem(PREF_KEY)) || {}; } catch { return {}; } })(),
);
function savePrefs() {
  try { localStorage.setItem(PREF_KEY, JSON.stringify(prefs)); } catch { /* private mode */ }
}

/* ---------------- state ---------------- */

const state = {
  view: null,          // {type:'single', info} | {type:'batch', title, items, platform...}
  quality: 'best',
  trimStart: '',
  trimEnd: '',
  moreOpen: false,
  status: null,
  jobs: [],
  infoController: null,
  pollTimer: null,
};
const isLocal = ['127.0.0.1', 'localhost', '[::1]', '::1'].includes(location.hostname);

/* ---------------- helpers ---------------- */

class ApiError extends Error {
  constructor(message, detail) { super(message); this.detail = detail; }
}

async function api(path, { method = 'GET', body, signal } = {}) {
  const opts = { method, signal, headers: {} };
  if (method !== 'GET') {
    opts.headers['Content-Type'] = 'application/json';
    opts.headers['X-RealConvert'] = '1';
    opts.body = JSON.stringify(body || {});
  }
  let res;
  try {
    res = await fetch(path, opts);
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError('Can’t reach RealConvert. Is its window still open?');
  }
  let data = null;
  try { data = await res.json(); } catch { /* not json */ }
  if (!res.ok) throw new ApiError((data && data.error) || `Something went wrong (${res.status}).`, data && data.detail);
  return data;
}

function fmtBytes(n) {
  if (n == null || !isFinite(n)) return '';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (n >= 1000 && i < units.length - 1) { n /= 1000; i++; }
  return `${n >= 100 || i === 0 ? Math.round(n) : n.toFixed(1)} ${units[i]}`;
}
function fmtEta(s) {
  if (s == null || !isFinite(s)) return '';
  s = Math.max(0, Math.round(s));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${String(s % 60).padStart(2, '0')}s`;
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`;
}

let toastTimer = null;
function toast(msg, isError = false) {
  const el = $('#toast');
  el.textContent = msg;
  el.classList.toggle('err', isError);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, isError ? 5000 : 2600);
}

function extractUrls(text) {
  const found = (text.match(/https?:\/\/[^\s<>"'`]+/gi) || []).map((u) => u.replace(/[),.;!]+$/, ''));
  if (found.length) return [...new Set(found)];
  const t = text.trim();
  if (/^[\w-]+(\.[\w-]+)+\/\S*$/i.test(t)) return [`https://${t}`];
  return [];
}

/* ---------------- link input ---------------- */

const urlInput = $('#urlInput');

$('#linkIcon').innerHTML = icon('link');
$('#openFolderBtn').innerHTML = icon('folder');
$('#settingsBtn').innerHTML = icon('gear');
$('#settingsClose').innerHTML = icon('x');

$('#linkForm').addEventListener('submit', (e) => {
  e.preventDefault();
  go(urlInput.value);
});

urlInput.addEventListener('paste', () => {
  setTimeout(() => { if (extractUrls(urlInput.value).length) go(urlInput.value); }, 0);
});

$('#pasteBtn').addEventListener('click', async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (!text.trim()) { toast('Your clipboard is empty.'); return; }
    urlInput.value = text.trim();
    go(urlInput.value);
  } catch {
    urlInput.focus();
    toast('Press Ctrl+V (or ⌘V) to paste your link.');
  }
});

function go(text) {
  const urls = extractUrls(text || '');
  if (!urls.length) {
    renderError('Paste a link to a video first — for example https://www.youtube.com/watch?v=…');
    return;
  }
  if (urls.length > 1) {
    urlInput.value = urls.join(' ');
    showBatch({ title: `${urls.length} links`, items: urls.map((u) => ({ url: u, title: u })), kind: 'links' });
    return;
  }
  urlInput.value = urls[0];
  fetchInfo(urls[0]);
}

async function fetchInfo(url) {
  if (state.infoController) state.infoController.abort();
  const controller = new AbortController();
  state.infoController = controller;
  renderLoading();
  $('#goBtn').disabled = true;
  try {
    const info = await api('/api/info', { method: 'POST', body: { url }, signal: controller.signal });
    if (controller.signal.aborted) return;
    if (info.kind === 'playlist') {
      showBatch({
        title: info.title, items: info.entries, kind: 'playlist', platform: info.platform,
        platform_key: info.platform_key, uploader: info.uploader, truncated: info.truncated,
      });
    } else {
      state.view = { type: 'single', info };
      state.quality = 'best';
      state.trimStart = state.trimEnd = '';
      renderView();
    }
  } catch (err) {
    if (err.name === 'AbortError') return;
    renderError(err.message, err.detail);
  } finally {
    if (state.infoController === controller) {
      state.infoController = null;
      $('#goBtn').disabled = false;
    }
  }
}

function showBatch(batch) {
  state.view = { type: 'batch', ...batch };
  state.quality = 'best';
  state.trimStart = state.trimEnd = '';
  renderView();
}

/* ---------------- result area ---------------- */

const resultArea = $('#resultArea');
let loadingTimer = null;

function renderLoading() {
  clearTimeout(loadingTimer);
  resultArea.innerHTML = `
    <div class="card loading">
      <div class="skeleton box"></div>
      <div class="lines">
        <div class="skeleton line" style="width:85%"></div>
        <div class="skeleton line" style="width:55%"></div>
        <div class="loading-text"><span class="spinner"></span><span id="loadingMsg">Reading link…</span></div>
      </div>
    </div>`;
  loadingTimer = setTimeout(() => {
    const el = $('#loadingMsg');
    if (el) el.textContent = 'Still working — some sites take a few seconds…';
  }, 6000);
}

function renderError(message, detail) {
  clearTimeout(loadingTimer);
  state.view = null;
  resultArea.innerHTML = `
    <div class="card error-card" role="alert">
      ${icon('alert')}
      <div>
        <p>${esc(message)}</p>
        ${detail ? `<details><summary>Details</summary><code>${esc(detail)}</code></details>` : ''}
      </div>
    </div>`;
}

function currentMode() {
  const v = state.view;
  if (v && v.type === 'single' && !v.info.has_video) return 'audio';
  return prefs.mode === 'audio' ? 'audio' : 'video';
}
function currentFormat() {
  return currentMode() === 'audio' ? prefs.audioFormat : prefs.videoFormat;
}
function qualityOptions() {
  const v = state.view;
  if (v && v.type === 'single' && v.info.qualities && v.info.qualities.length) return v.info.qualities;
  return RUNGS.map((r) => ({ value: r, label: `${r}p`, tag: qualityTag(r) }));
}

function renderView() {
  clearTimeout(loadingTimer);
  const v = state.view;
  if (!v) { resultArea.innerHTML = ''; return; }
  resultArea.innerHTML = `<div class="card">${v.type === 'single' ? mediaHTML(v.info) : batchHTML(v)}
    <div class="options" id="options"></div></div>`;
  renderOptions();
  if (v.type === 'batch') {
    resultArea.querySelectorAll('[data-remove]').forEach((btn) => btn.addEventListener('click', () => {
      v.items.splice(Number(btn.dataset.remove), 1);
      if (!v.items.length) { state.view = null; resultArea.innerHTML = ''; return; }
      if (v.kind === 'links') v.title = `${v.items.length} link${v.items.length === 1 ? '' : 's'}`;
      renderView();
    }));
  }
  resultArea.querySelectorAll('img[data-fallback]').forEach((img) => img.addEventListener('error', () => {
    img.replaceWith(Object.assign(document.createElement('span'), { className: img.dataset.fallback }));
  }));
}

function mediaHTML(info) {
  const orient = info.orientation === 'vertical' ? 'vertical' : info.orientation === 'square' ? 'square' : '';
  const thumb = info.thumbnail
    ? `<img src="${esc(info.thumbnail)}" alt="" data-fallback="ph" loading="lazy">`
    : icon(info.has_video ? 'film' : 'music', 'lg');
  const best = (info.qualities || [])[0];
  const badges = [`<span class="badge platform" data-p="${esc(info.platform_key)}">${esc(info.platform)}</span>`];
  if (info.orientation === 'vertical') badges.push('<span class="badge">Vertical</span>');
  else if (info.orientation === 'square') badges.push('<span class="badge">Square</span>');
  else if (info.orientation === 'horizontal') badges.push('<span class="badge">Landscape</span>');
  if (best) badges.push(`<span class="badge q">Up to ${esc(best.label)}${best.tag ? ' · ' + esc(best.tag) : ''}</span>`);
  if (!info.has_video) badges.push('<span class="badge">Audio only</span>');
  if (info.kind === 'multi') badges.push(`<span class="badge">${info.count} videos in this post</span>`);
  const meta = [];
  if (info.uploader) meta.push(esc(info.uploader));
  if (info.width && info.height) meta.push(`${info.width}×${info.height}`);
  if (info.filesize) meta.push(`≈ ${fmtBytes(info.filesize)}`);
  return `
    <div class="media">
      <div class="thumb ${orient}">${thumb}${info.duration_text ? `<span class="dur">${esc(info.duration_text)}</span>` : ''}</div>
      <div class="media-body">
        <div class="badges">${badges.join('')}</div>
        <h3 class="media-title" title="${esc(info.title)}">${esc(info.title)}</h3>
        <div class="meta">${meta.map((m) => `<span>${m}</span>`).join('')}</div>
      </div>
    </div>`;
}

function batchHTML(v) {
  const heading = v.kind === 'playlist'
    ? `${v.items.length} video${v.items.length === 1 ? '' : 's'}${v.truncated ? ' (first 300)' : ''}`
    : 'Several links';
  const rows = v.items.map((it, i) => `
    <li>
      <span class="n">${i + 1}</span>
      ${it.thumbnail ? `<img src="${esc(it.thumbnail)}" alt="" loading="lazy" data-fallback="ph">` : '<span class="ph"></span>'}
      <span class="t" title="${esc(it.title)}">${esc(it.title)}</span>
      ${it.duration_text ? `<span class="d">${esc(it.duration_text)}</span>` : ''}
      <button class="icon-btn danger" type="button" data-remove="${i}" title="Remove from list" aria-label="Remove">${icon('x', 'sm')}</button>
    </li>`).join('');
  return `
    <div class="batch-head">
      <div class="batch-icon">${icon('list', 'lg')}</div>
      <div style="min-width:0">
        <div class="badges">
          ${v.platform ? `<span class="badge platform" data-p="${esc(v.platform_key)}">${esc(v.platform)}</span>` : ''}
          <span class="badge q">${esc(heading)}</span>
        </div>
        <h3 class="media-title">${esc(v.title)}</h3>
        ${v.uploader ? `<div class="meta"><span>${esc(v.uploader)}</span></div>` : ''}
      </div>
    </div>
    <ul class="batch-list">${rows}</ul>`;
}

function renderOptions() {
  const box = $('#options');
  if (!box) return;
  const v = state.view;
  const mode = currentMode();
  const fmt = currentFormat();
  const single = v.type === 'single';
  const hasVideo = !single || v.info.has_video;
  const formats = mode === 'audio' ? AUDIO_FORMATS : VIDEO_FORMATS;
  const qualities = qualityOptions();
  if (state.quality !== 'best' && !qualities.some((q) => String(q.value) === String(state.quality))) state.quality = 'best';

  const best = qualities[0];
  const qualitySelect = mode === 'video' ? `
    <div class="opt-row">
      <span class="opt-label">Quality</span>
      <select class="select" id="qualitySel">
        <option value="best">Best available${single && best ? ` — ${best.label}${best.tag ? ' (' + best.tag + ')' : ''}` : ' (original)'}</option>
        ${qualities.map((q) => `<option value="${q.value}" ${String(state.quality) === String(q.value) ? 'selected' : ''}>
          ${single ? '' : 'Up to '}${esc(q.label)}${q.tag ? ' · ' + esc(q.tag) : ''}</option>`).join('')}
      </select>
    </div>` : '';
  const bitrateSelect = mode === 'audio' && fmt === 'mp3' ? `
    <div class="opt-row">
      <span class="opt-label">MP3 quality</span>
      <select class="select" id="bitrateSel">
        ${BITRATES.map((b) => `<option value="${b}" ${prefs.audioQuality === b ? 'selected' : ''}>${b} kbps${b === '320' ? ' — best' : ''}</option>`).join('')}
      </select>
    </div>` : '';

  const compatSwitch = mode === 'video' && (fmt === 'mp4' || fmt === 'mov') ? `
    <label class="switch">
      <input type="checkbox" id="compatChk" ${prefs.compat ? 'checked' : ''}>
      <span class="track"></span>
      <span class="switch-text"><b>Make it play everywhere (H.264)</b>
        <span class="hint">If the best version uses a newer codec (common for 4K YouTube or some TikToks), convert it
          so it opens in every player, phone and editor. Takes longer for big videos. Turn off to keep the exact
          original stream.</span></span>
    </label>` : '';
  const trim = single ? `
    <div class="opt-row">
      <span class="opt-label">Trim (optional)</span>
      <div class="trim">
        <label>Start<input class="input" id="trimStart" placeholder="0:00" value="${esc(state.trimStart)}" inputmode="numeric"></label>
        <label>End<input class="input" id="trimEnd" placeholder="end" value="${esc(state.trimEnd)}" inputmode="numeric"></label>
      </div>
      <span class="hint">Times like 1:30 or 90. Leave empty to keep the whole thing.</span>
    </div>` : '';
  const moreBody = compatSwitch + trim;

  const n = v.type === 'batch' ? v.items.length : 1;
  const fmtLabel = formats.find((f) => f.id === fmt)?.label || fmt.toUpperCase();
  let detail = '';
  if (mode === 'video') {
    const q = qualities.find((x) => String(x.value) === String(state.quality));
    detail = q ? q.label : 'Best quality';
  } else if (fmt === 'mp3') detail = `${prefs.audioQuality} kbps`;
  const cta = v.type === 'batch'
    ? `Download all ${n} as ${fmt === 'original' ? 'original audio' : fmtLabel}`
    : `Download ${fmt === 'original' ? 'original audio' : fmtLabel}${detail ? ' · ' + detail : ''}`;

  box.innerHTML = `
    <div class="opt-row">
      <div class="segmented" role="group" aria-label="Video or audio">
        <button type="button" data-mode="video" aria-pressed="${mode === 'video'}" ${hasVideo ? '' : 'disabled title="This link has no video"'}>${icon('film', 'sm')} Video</button>
        <button type="button" data-mode="audio" aria-pressed="${mode === 'audio'}">${icon('music', 'sm')} Audio</button>
      </div>
    </div>
    <div class="opt-row">
      <span class="opt-label">Format</span>
      <div class="chips">
        ${formats.map((f) => `<button type="button" class="chip" data-fmt="${f.id}" aria-pressed="${f.id === fmt}">
          <b>${f.label}</b><small>${f.note}</small></button>`).join('')}
      </div>
    </div>
    ${qualitySelect}${bitrateSelect}
    ${moreBody ? `<details class="more" id="moreBox" ${state.moreOpen ? 'open' : ''}>
      <summary>${icon('sliders', 'sm')} More options<span class="chev">${icon('chevron', 'sm')}</span></summary>
      <div class="more-body">${moreBody}</div></details>` : ''}
    <button type="button" class="btn big primary" id="downloadBtn">${icon('download')} ${esc(cta)}</button>`;

  box.querySelectorAll('[data-mode]').forEach((b) => b.addEventListener('click', () => {
    prefs.mode = b.dataset.mode; savePrefs(); renderOptions();
  }));
  box.querySelectorAll('[data-fmt]').forEach((b) => b.addEventListener('click', () => {
    if (currentMode() === 'audio') prefs.audioFormat = b.dataset.fmt; else prefs.videoFormat = b.dataset.fmt;
    savePrefs(); renderOptions();
  }));
  $('#qualitySel')?.addEventListener('change', (e) => { state.quality = e.target.value; renderOptions(); });
  $('#bitrateSel')?.addEventListener('change', (e) => { prefs.audioQuality = e.target.value; savePrefs(); renderOptions(); });
  $('#compatChk')?.addEventListener('change', (e) => { prefs.compat = e.target.checked; savePrefs(); });
  $('#trimStart')?.addEventListener('input', (e) => { state.trimStart = e.target.value; });
  $('#trimEnd')?.addEventListener('input', (e) => { state.trimEnd = e.target.value; });
  $('#moreBox')?.addEventListener('toggle', (e) => { state.moreOpen = e.target.open; });
  $('#downloadBtn').addEventListener('click', startDownload);
}

async function startDownload() {
  const v = state.view;
  if (!v) return;
  const btn = $('#downloadBtn');
  btn.disabled = true;
  const base = {
    format: currentFormat(),
    quality: currentMode() === 'video' ? state.quality : 'best',
    audio_quality: prefs.audioQuality,
    compat: prefs.compat,
  };
  try {
    if (v.type === 'single') {
      const info = v.info;
      await api('/api/download', {
        method: 'POST',
        body: {
          ...base, url: info.url, trim_start: state.trimStart, trim_end: state.trimEnd,
          title: info.title, thumbnail: info.thumbnail, platform: info.platform, platform_key: info.platform_key,
        },
      });
      toast('Added to your downloads');
    } else {
      for (const it of v.items) {
        await api('/api/download', {
          method: 'POST',
          body: {
            ...base, url: it.url, title: it.title !== it.url ? it.title : null, thumbnail: it.thumbnail,
            platform: v.platform, platform_key: v.platform_key,
          },
        });
      }
      toast(`Added ${v.items.length} downloads`);
    }
    await refreshJobs();
    const section = $('#downloadsSection');
    const rect = section.getBoundingClientRect();
    if (rect.top > window.innerHeight - 80) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    toast(err.message, true);
  } finally {
    btn.disabled = false;
  }
}

/* ---------------- downloads list ---------------- */

const jobList = $('#jobList');

function jobStageText(j) {
  const pct = j.progress != null ? `${Math.floor(j.progress * 100)}%` : '';
  switch (j.status) {
    case 'queued': return 'Waiting in line…';
    case 'preparing': return j.stage || 'Reading link…';
    case 'downloading': {
      const parts = [j.stage || 'Downloading'];
      if (pct) parts.push(pct);
      if (j.downloaded && j.total) parts.push(`${fmtBytes(j.downloaded)} of ${fmtBytes(j.total)}`);
      else if (j.downloaded) parts.push(fmtBytes(j.downloaded));
      if (j.speed) parts.push(`${fmtBytes(j.speed)}/s`);
      if (j.eta != null && j.eta > 0) parts.push(`${fmtEta(j.eta)} left`);
      return parts.join(' · ');
    }
    case 'processing': return [j.stage || 'Processing…', pct, j.speed_text].filter(Boolean).join(' · ');
    case 'done': {
      const size = j.files.reduce((a, f) => a + (f.size || 0), 0);
      return `Saved${j.files.length > 1 ? ` · ${j.files.length} files` : ''}${size ? ' · ' + fmtBytes(size) : ''}`;
    }
    case 'error': return 'Failed';
    case 'cancelled': return 'Cancelled';
    default: return j.stage || '';
  }
}

function jobQualityText(j) {
  if (j.kind === 'audio') return j.format === 'mp3' ? `${j.audio_quality} kbps` : '';
  return j.quality === 'best' ? 'Best' : `${j.quality}p`;
}

function jobActionsHTML(j) {
  const b = (act, ico, title, cls = '') =>
    `<button class="icon-btn ${cls}" type="button" data-act="${act}" title="${title}" aria-label="${title}">${icon(ico)}</button>`;
  if (['queued', 'preparing', 'downloading', 'processing'].includes(j.status)) return b('cancel', 'x', 'Cancel', 'danger');
  if (j.status === 'done') {
    const save = `<a class="icon-btn ${isLocal ? '' : 'accent'}" href="/api/jobs/${j.id}/file?index=0" download
      title="${isLocal ? 'Save a copy somewhere else' : 'Save to this device'}" aria-label="Save a copy">${icon(isLocal ? 'download' : 'phone')}</a>`;
    if (!isLocal) return save + b('remove', 'trash', 'Remove from list');
    return b('play', 'play', 'Open file', 'accent') + b('folder', 'folder', 'Show in folder') + save
      + b('remove', 'trash', 'Remove from list');
  }
  return b('retry', 'retry', 'Try again', 'accent') + b('remove', 'trash', 'Remove from list');
}

function jobSignature(j) {
  return [j.status, j.files.length, j.error, j.thumbnail, j.title].join('|');
}

function jobHTML(j) {
  const thumb = j.thumbnail
    ? `<img src="${esc(j.thumbnail)}" alt="" loading="lazy" data-fallback="ph">`
    : icon(j.kind === 'audio' ? 'music' : 'film');
  const state = j.status === 'done' ? `<span class="state">${icon('check')}</span>`
    : j.status === 'error' ? `<span class="state">${icon('x')}</span>` : '';
  const active = ['queued', 'preparing', 'downloading', 'processing'].includes(j.status);
  const qual = jobQualityText(j);
  return `
    <div class="job-thumb">${thumb}${state}</div>
    <div class="job-main">
      <div class="job-title" title="${esc(j.title)}">${esc(j.title)}</div>
      <div class="job-meta">
        <span class="pill">${esc(j.format === 'original' ? 'AUDIO' : j.format.toUpperCase())}</span>
        ${qual ? `<span>${esc(qual)}</span>` : ''}
        ${j.trimmed ? '<span>Clip</span>' : ''}
        <span class="job-stage" data-stage>${esc(jobStageText(j))}</span>
      </div>
      ${active ? '<div class="bar" data-bar><div></div></div>' : ''}
      ${j.status === 'done' && j.files.length ? `<div class="job-files" title="${esc(j.files.map((f) => f.name).join('\n'))}">${esc(j.files.map((f) => f.name).join(', '))}</div>` : ''}
      ${j.status === 'error' ? `<div class="job-error">${esc(j.error)}
        ${j.error_detail ? `<details><summary>Details</summary><code>${esc(j.error_detail)}</code></details>` : ''}</div>` : ''}
    </div>
    <div class="job-actions">${jobActionsHTML(j)}</div>`;
}

function updateJobLive(li, j) {
  const stage = li.querySelector('[data-stage]');
  if (stage) stage.textContent = jobStageText(j);
  const bar = li.querySelector('[data-bar]');
  if (bar) {
    const indeterminate = j.progress == null || j.status === 'queued' || j.status === 'preparing';
    bar.classList.toggle('indeterminate', indeterminate && j.status !== 'queued');
    bar.firstElementChild.style.width = indeterminate ? (j.status === 'queued' ? '0%' : '') : `${Math.max(2, j.progress * 100)}%`;
  }
}

function renderJobs() {
  const jobs = state.jobs;
  $('#downloadsSection').hidden = !jobs.length;
  $('#clearBtn').hidden = !jobs.some((j) => !['queued', 'preparing', 'downloading', 'processing'].includes(j.status));
  const existing = new Map([...jobList.children].map((li) => [li.dataset.id, li]));
  let prev = null;
  for (const j of jobs) {
    let li = existing.get(j.id);
    if (!li) {
      li = document.createElement('li');
      li.dataset.id = j.id;
    }
    existing.delete(j.id);
    const sig = jobSignature(j);
    if (li.dataset.sig !== sig) {
      li.className = `job ${j.status}`;
      li.innerHTML = jobHTML(j);
      li.dataset.sig = sig;
      li.querySelectorAll('img[data-fallback]').forEach((img) => img.addEventListener('error', () => {
        img.replaceWith(Object.assign(document.createElement('span'), { innerHTML: icon(j.kind === 'audio' ? 'music' : 'film') }));
      }));
    }
    updateJobLive(li, j);
    const want = prev ? prev.nextSibling : jobList.firstChild;
    if (want !== li) jobList.insertBefore(li, want);
    prev = li;
  }
  existing.forEach((li) => li.remove());
  const activeCount = jobs.filter((j) => ['queued', 'preparing', 'downloading', 'processing'].includes(j.status)).length;
  document.title = activeCount ? `(${activeCount}) RealConvert` : 'RealConvert';
}

jobList.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-act]');
  if (!btn) return;
  const id = btn.closest('li').dataset.id;
  const act = btn.dataset.act;
  try {
    if (act === 'cancel') await api(`/api/jobs/${id}/cancel`, { method: 'POST' });
    else if (act === 'remove') await api(`/api/jobs/${id}/remove`, { method: 'POST' });
    else if (act === 'retry') await api(`/api/jobs/${id}/retry`, { method: 'POST' });
    else if (act === 'play') await api(`/api/jobs/${id}/open`, { method: 'POST', body: { target: 'file' } });
    else if (act === 'folder') await api(`/api/jobs/${id}/open`, { method: 'POST', body: { target: 'folder' } });
    await refreshJobs();
  } catch (err) {
    toast(err.message, true);
  }
});

$('#clearBtn').addEventListener('click', async () => {
  try { await api('/api/jobs/clear', { method: 'POST' }); await refreshJobs(); } catch (err) { toast(err.message, true); }
});

let lastDoneIds = null;
async function refreshJobs() {
  try {
    const data = await api('/api/jobs');
    state.jobs = data.jobs;
    const doneIds = new Set(data.jobs.filter((j) => j.status === 'done').map((j) => j.id));
    if (lastDoneIds) {
      const fresh = data.jobs.filter((j) => doneIds.has(j.id) && !lastDoneIds.has(j.id));
      if (fresh.length === 1) toast(`Saved: ${fresh[0].files[0]?.name || fresh[0].title}`);
      else if (fresh.length > 1) toast(`${fresh.length} downloads finished`);
    }
    lastDoneIds = doneIds;
    if (data.restart_needed) showRestartBanner();
    renderJobs();
  } catch { /* server gone; try again next tick */ }
  schedulePoll();
}

function schedulePoll() {
  clearTimeout(state.pollTimer);
  const active = state.jobs.some((j) => ['queued', 'preparing', 'downloading', 'processing'].includes(j.status));
  state.pollTimer = setTimeout(refreshJobs, active ? 700 : 4000);
}

/* ---------------- status, folder, settings ---------------- */

function showRestartBanner() {
  const b = $('#banner');
  b.innerHTML = `${icon('retry')} <span>The download engine was updated. Close RealConvert's window and open it again to use the new version.</span>`;
  b.hidden = false;
}

function renderStatus() {
  const s = state.status;
  if (!s) return;
  const folder = $('#folderPath');
  folder.textContent = s.settings.output_dir;
  folder.title = isLocal ? 'Open this folder' : s.settings.output_dir;
  $('#changeFolderBtn').hidden = !isLocal;
  $('#openFolderBtn').hidden = !isLocal;
  const parts = [`yt-dlp ${esc(s.ytdlp_version)}`];
  parts.push(s.ffmpeg ? `ffmpeg ${esc(s.ffmpeg_version || '')}` : '<b style="color:var(--err)">ffmpeg missing</b>');
  parts.push(s.js_runtime ? `YouTube helper: ${esc(s.js_runtime)}` : '<span style="color:var(--warn)">no YouTube helper (Deno)</span>');
  $('#engineInfo').innerHTML = `Engine: ${parts.join(' · ')} · <button class="link-btn" id="footerUpdateBtn" type="button">Update engine</button>`;
  $('#footerUpdateBtn').addEventListener('click', updateEngine);
  $('#engineDetails').innerHTML = parts.join('<br>');
  if (s.restart_needed) showRestartBanner();
}

async function loadStatus() {
  try {
    state.status = await api('/api/status');
    renderStatus();
  } catch (err) {
    toast(err.message, true);
  }
}

async function openOutputFolder() {
  try { await api('/api/open-folder', { method: 'POST' }); } catch (err) { toast(err.message, true); }
}
$('#openFolderBtn').addEventListener('click', openOutputFolder);
$('#folderPath').addEventListener('click', () => { if (isLocal) openOutputFolder(); });
$('#changeFolderBtn').addEventListener('click', () => openSettings(true));

async function updateEngine() {
  const buttons = [$('#updateBtn'), $('#footerUpdateBtn')].filter(Boolean);
  buttons.forEach((b) => { b.disabled = true; b.dataset.label = b.textContent; b.textContent = 'Updating…'; });
  toast('Checking for engine updates…');
  try {
    const res = await api('/api/update', { method: 'POST' });
    toast(res.message);
    await loadStatus();
  } catch (err) {
    toast(err.message, true);
  } finally {
    buttons.forEach((b) => { if (b.isConnected) { b.disabled = false; b.textContent = b.dataset.label || 'Update engine'; } });
  }
}
$('#updateBtn').addEventListener('click', updateEngine);

const dialog = $('#settingsDialog');
const browserSel = $('#setBrowser');

function openSettings(focusFolder = false) {
  const s = state.status;
  if (!s) return;
  browserSel.innerHTML = `<option value="">Don't use cookies</option>` + s.browsers
    .map((b) => `<option value="${b}">${BROWSER_NAMES[b] || b}</option>`).join('');
  $('#setOutputDir').value = s.settings.output_dir || '';
  browserSel.value = s.settings.cookies_browser || '';
  $('#setCookieFile').value = s.settings.cookies_file || '';
  $('#setParallel').value = String(s.settings.max_parallel || 2);
  $('#browseBtn').hidden = !isLocal;
  $('#settingsError').hidden = true;
  if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
  if (focusFolder) $('#setOutputDir').select();
}
$('#settingsBtn').addEventListener('click', () => openSettings());

$('#browseBtn').addEventListener('click', async () => {
  const btn = $('#browseBtn');
  btn.disabled = true;
  try {
    const res = await api('/api/pick-folder', { method: 'POST' });
    if (res.path) $('#setOutputDir').value = res.path;
  } catch (err) {
    $('#settingsError').textContent = err.message;
    $('#settingsError').hidden = false;
  } finally {
    btn.disabled = false;
  }
});

$('#settingsSave').addEventListener('click', async () => {
  const err = $('#settingsError');
  err.hidden = true;
  try {
    await api('/api/settings', {
      method: 'POST',
      body: {
        output_dir: $('#setOutputDir').value,
        cookies_browser: browserSel.value,
        cookies_file: $('#setCookieFile').value,
        max_parallel: $('#setParallel').value,
      },
    });
    dialog.close();
    toast('Settings saved');
    await loadStatus();
  } catch (e) {
    err.textContent = e.message;
    err.hidden = false;
  }
});

/* ---------------- start ---------------- */

loadStatus();
refreshJobs();
urlInput.focus();
