// Stem mixer (UVR5 UI). Runs as the js_on_load of a gr.HTML, so `element`, `props` and
// `watch` come from Gradio. props.value = {name, stems: [{label, file: {url}}]} or null.
//
// Stems are decoded into AudioBuffers on the first Play/Download and started with the same
// AudioContext time, so they stay sample-accurate in sync (separate <audio> tags would drift).
// Each one goes through its own GainNode (volume, mute, solo) into a master GainNode.

const L = props.labels;
let ctx = null;
let master = null;
let stems = [];        // {label, url, buffer, gain, volume, muted, solo, failed, row}
let sources = [];      // AudioBufferSourceNodes of the current playback (single use)
let loading = null;    // Promise while the stems are being decoded
let generation = 0;    // bumped on every new value, so stale decodes are dropped
let playing = false;
let startedAt = 0;     // AudioContext time at which position 0 would have played
let offset = 0;        // position (seconds) while paused
let duration = 0;
let seeking = false;
let frame = 0;
let ui = {};

const make = (tag, attrs = {}, text) => {
  const node = document.createElement(tag);
  Object.assign(node, attrs);
  if (text !== undefined) node.textContent = text;
  return node;
};
const clock = (seconds) => {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

// Created on the first click (autoplay policy), at the stems' sample rate when it is known,
// so decodeAudioData doesn't resample them and the downloaded mix keeps their rate
function audioContext() {
  const rate = props.value && props.value.sample_rate;
  if (ctx && rate && ctx.sampleRate !== rate) {
    ctx.close();
    ctx = null;
  }
  if (!ctx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    try {
      ctx = rate ? new AudioContextClass({ sampleRate: rate }) : new AudioContextClass();
    } catch (error) {
      ctx = new AudioContextClass(); // the browser doesn't support that rate
    }
    master = ctx.createGain();
    master.connect(ctx.destination);
  }
  return ctx;
}

// Solo wins over mute; when any stem is soloed, only the soloed ones are heard
function gainOf(stem) {
  if (stem.solo) return stem.volume;
  if (stem.muted || stems.some((s) => s.solo && s.buffer)) return 0;
  return stem.volume;
}

function applyGains() {
  if (!ctx) return;
  for (const stem of stems) {
    if (stem.gain) stem.gain.gain.setTargetAtTime(gainOf(stem), ctx.currentTime, 0.01);
  }
}

function setStatus(text) {
  if (ui.status) ui.status.textContent = text;
}

function load() {
  if (loading) return loading;
  const gen = generation;
  const ac = audioContext();
  setStatus(L.loading);
  loading = Promise.all(stems.map(async (stem) => {
    try {
      const response = await fetch(stem.url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      stem.buffer = await ac.decodeAudioData(await response.arrayBuffer());
      stem.gain = ac.createGain();
      stem.gain.connect(master);
    } catch (error) {
      stem.failed = true;
      console.warn("[UVR5 UI mixer] could not load", stem.label, error);
    }
  })).then(() => {
    if (gen !== generation) return;
    duration = Math.max(0, ...stems.filter((s) => s.buffer).map((s) => s.buffer.duration));
    stems.forEach(updateRow);
    applyGains();
    setStatus("");
    updateTime();
  });
  return loading;
}

function position() {
  return playing ? Math.min(ctx.currentTime - startedAt, duration) : offset;
}

function stopSources() {
  for (const source of sources) {
    try { source.stop(); } catch (error) { /* already stopped */ }
    source.disconnect();
  }
  sources = [];
}

async function play() {
  const gen = generation;
  await load();
  if (gen !== generation || playing || !duration) return;
  const ac = audioContext();
  if (ac.state === "suspended") await ac.resume();
  if (offset >= duration) offset = 0;
  const when = ac.currentTime + 0.05;
  sources = stems.filter((s) => s.buffer).map((stem) => {
    const source = ac.createBufferSource();
    source.buffer = stem.buffer;
    source.connect(stem.gain);
    source.start(when, Math.min(offset, stem.buffer.duration));
    return source;
  });
  startedAt = when - offset;
  playing = true;
  updateTransport();
  tick();
}

function pause() {
  offset = position();
  stopSources();
  playing = false;
  cancelAnimationFrame(frame);
  updateTransport();
}

function stop() {
  stopSources();
  playing = false;
  offset = 0;
  cancelAnimationFrame(frame);
  updateTime();
  updateTransport();
}

function seekTo(seconds) {
  const resume = playing;
  if (playing) pause();
  offset = Math.min(Math.max(seconds, 0), duration);
  updateTime();
  if (resume) play();
}

function tick() {
  updateTime();
  if (!playing) return;
  if (position() >= duration) {
    stop();
    return;
  }
  frame = requestAnimationFrame(tick);
}

function updateTime() {
  if (!ui.time) return;
  const now = position();
  ui.time.textContent = `${clock(now)} / ${clock(duration)}`;
  if (!seeking) ui.seek.value = duration ? String(Math.round((now / duration) * 1000)) : "0";
  ui.seek.setAttribute("aria-valuetext", ui.time.textContent);
}

function updateTransport() {
  if (!ui.play) return;
  ui.play.textContent = playing ? "⏸" : "▶";
  ui.play.setAttribute("aria-label", playing ? L.pause : L.play);
  ui.play.title = playing ? L.pause : L.play;
}

function updateRow(stem) {
  const { row, mute, solo, volume, percent, error } = stem.row;
  mute.setAttribute("aria-pressed", String(stem.muted));
  solo.setAttribute("aria-pressed", String(stem.solo));
  percent.textContent = `${Math.round(stem.volume * 100)}%`;
  volume.setAttribute("aria-valuetext", percent.textContent);
  row.classList.toggle("unavailable", stem.failed);
  error.hidden = !stem.failed;
  for (const control of [mute, solo, volume]) control.disabled = stem.failed;
}

// Float WAV, so a mix louder than 0 dBFS (stems above 100%) isn't clipped
function encodeWav(buffer) {
  const channels = buffer.numberOfChannels;
  const frames = buffer.length;
  const bytes = frames * channels * 4;
  const view = new DataView(new ArrayBuffer(44 + bytes));
  const text = (at, value) => [...value].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, 36 + bytes, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 3, true); // WAVE_FORMAT_IEEE_FLOAT
  view.setUint16(22, channels, true);
  view.setUint32(24, buffer.sampleRate, true);
  view.setUint32(28, buffer.sampleRate * channels * 4, true);
  view.setUint16(32, channels * 4, true);
  view.setUint16(34, 32, true);
  text(36, "data");
  view.setUint32(40, bytes, true);
  const data = Array.from({ length: channels }, (_, c) => buffer.getChannelData(c));
  let at = 44;
  for (let i = 0; i < frames; i++) {
    for (let c = 0; c < channels; c++, at += 4) view.setFloat32(at, data[c][i], true);
  }
  return view.buffer;
}

async function downloadMix() {
  const gen = generation;
  const name = props.value && props.value.name;
  await load();
  const ready = stems.filter((s) => s.buffer);
  if (gen !== generation || !ready.length) return;
  ui.export.disabled = true;
  setStatus(L.loading);
  try {
    const rate = ready[0].buffer.sampleRate;
    const offline = new OfflineAudioContext(2, Math.ceil(duration * rate), rate);
    for (const stem of ready) {
      const source = offline.createBufferSource();
      const gain = offline.createGain();
      source.buffer = stem.buffer;
      gain.gain.value = gainOf(stem);
      source.connect(gain).connect(offline.destination);
      source.start(0);
    }
    const blob = new Blob([encodeWav(await offline.startRendering())], { type: "audio/wav" });
    const link = make("a", { href: URL.createObjectURL(blob), download: `${name || "mix"}.wav` });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 60000);
  } finally {
    ui.export.disabled = false;
    setStatus("");
  }
}

function render() {
  generation++;
  stopSources();
  playing = false;
  cancelAnimationFrame(frame);
  for (const stem of stems) if (stem.gain) stem.gain.disconnect();
  stems = [];
  loading = null;
  offset = 0;
  duration = 0;
  ui = {};

  const root = element.querySelector(".uvr-mixer");
  if (!root) return;
  root.replaceChildren();
  const value = props.value;
  if (!value || !Array.isArray(value.stems) || !value.stems.length) return;

  ui.play = make("button", { type: "button", className: "play" });
  ui.play.addEventListener("click", () => (playing ? pause() : play()));
  const stopButton = make("button", { type: "button", title: L.stop }, "■");
  stopButton.setAttribute("aria-label", L.stop);
  stopButton.addEventListener("click", stop);
  ui.seek = make("input", { type: "range", min: "0", max: "1000", step: "1", value: "0", className: "seek" });
  ui.seek.setAttribute("aria-label", L.position);
  ui.seek.addEventListener("input", () => {
    seeking = true;
    ui.time.textContent = `${clock((ui.seek.value / 1000) * duration)} / ${clock(duration)}`;
  });
  ui.seek.addEventListener("change", () => {
    seeking = false;
    seekTo((ui.seek.value / 1000) * duration);
  });
  ui.time = make("span", { className: "time" }, "0:00 / 0:00");
  ui.export = make("button", { type: "button", className: "export" }, `⬇ ${L.export}`);
  ui.export.addEventListener("click", downloadMix);
  const transport = make("div", { className: "transport" });
  transport.append(ui.play, stopButton, ui.seek, ui.time, ui.export);

  ui.status = make("div", { className: "status" });
  ui.status.setAttribute("aria-live", "polite");
  root.append(transport, ui.status);

  for (const item of value.stems) {
    const stem = {
      label: item.label,
      url: item.file && item.file.url,
      buffer: null,
      gain: null,
      volume: 1,
      muted: false,
      solo: false,
      failed: !(item.file && item.file.url),
    };
    const row = make("div", { className: "row" });
    row.setAttribute("role", "group");
    row.setAttribute("aria-label", stem.label);
    const name = make("span", { className: "label", title: stem.label }, stem.label);
    const mute = make("button", { type: "button", className: "toggle", title: L.mute }, "M");
    mute.setAttribute("aria-label", `${L.mute}: ${stem.label}`);
    mute.addEventListener("click", () => {
      stem.muted = !stem.muted;
      updateRow(stem);
      applyGains();
    });
    const solo = make("button", { type: "button", className: "toggle", title: L.solo }, "S");
    solo.setAttribute("aria-label", `${L.solo}: ${stem.label}`);
    solo.addEventListener("click", () => {
      stem.solo = !stem.solo;
      updateRow(stem);
      applyGains();
    });
    const volume = make("input", { type: "range", min: "0", max: "150", step: "1", value: "100", className: "volume" });
    volume.setAttribute("aria-label", `${L.volume}: ${stem.label}`);
    volume.addEventListener("input", () => {
      stem.volume = Number(volume.value) / 100;
      updateRow(stem);
      applyGains();
    });
    const percent = make("span", { className: "percent" });
    const error = make("span", { className: "error", hidden: true }, L.unplayable);
    row.append(name, mute, solo, volume, percent, error);
    root.append(row);
    stem.row = { row, mute, solo, volume, percent, error };
    stems.push(stem);
    updateRow(stem);
  }
  updateTransport();
  updateTime();
}

render();
watch("value", render);
