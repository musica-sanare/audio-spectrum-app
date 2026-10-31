// The audio-spectrum page: settings built from the preset schema, previews rendered by the server.
// Every frame comes from the same code as the final video; this file only collects settings and shows results.

const LANGUAGES = { ja: "日本語", en: "English", es: "Español", fr: "Français" };
const SECTIONS = [
  ["colors", ["background", "foreground", "fill"]],
  ["analysis", ["analysis"]],
  ["look", ["look"]],
  ["fx", ["fx"]],
];
const HIDDEN_KEYS = new Set(["schema_version", "name"]);
const UPDATE_DELAY_MS = 150;
const RENDER_POLL_MS = 250;

const $ = (id) => document.getElementById(id);
const state = {
  token: null,
  language: "en",
  texts: null,
  schema: null,
  preset: null,
  song: null,
  previewRequest: 0,
  timer: null,
  stillUrl: null,
  clipUrl: null,
  fields: new Map(),
  outputDir: null,
  renderTimer: null,
};

// --- Text --------------------------------------------------------------------------------------------------------

function t(id, params = {}) {
  const text = state.texts?.messages[id] ?? id;
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
}

function keyText(key) {
  return state.texts?.keys[key] ?? { label: key, help: "" };
}

function storedLanguage() {
  try {
    return localStorage.getItem("language");
  } catch {
    return null;
  }
}

function rememberLanguage(language) {
  try {
    localStorage.setItem("language", language);
  } catch {
    // Private windows may refuse storage; the choice then lasts for this page only.
  }
}

function browserLanguage() {
  for (const tag of navigator.languages ?? [navigator.language]) {
    const language = tag.slice(0, 2).toLowerCase();
    if (language in LANGUAGES) return language;
  }
  return "en";
}

async function setLanguage(language) {
  state.texts = await (await fetch(`/static/i18n/${language}.json`)).json();
  state.language = language;
  document.documentElement.lang = language;
  for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
  for (const element of document.querySelectorAll("[data-i18n-placeholder]")) {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  }
  showSong();
  showFolder();
  if (state.preset) buildForm();
}

// --- Server ------------------------------------------------------------------------------------------------------

class ApiError extends Error {
  constructor(status, body) {
    super(body.message ?? "");
    this.status = status;
    this.code = body.code ?? "unknown";
    this.errors = body.errors ?? [];
    this.detail = body;
  }
}

async function api(path, body) {
  const options = { headers: { "X-Token": state.token } };
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = {};
    try {
      detail = await response.json();
    } catch {
      detail = { message: response.statusText };
    }
    throw new ApiError(response.status, detail);
  }
  return response;
}

function showError(error) {
  if (!error) {
    $("error").hidden = true;
    return;
  }
  const code = error instanceof ApiError ? error.code : "unknown";
  const title = t(`error.${code}`);
  $("error-title").textContent = title === `error.${code}` ? t("error.unknown") : title;
  $("error-message").textContent = error.message;
  $("error").hidden = false;
}

// --- Schema and form ---------------------------------------------------------------------------------------------

function definition(reference) {
  return state.schema.$defs[reference.split("/").pop()];
}

// The schema of a top-level key; for the look, the variant of the current preset's kind.
function tableSchema(key) {
  const field = state.schema.properties[key];
  if (field.$ref) return definition(field.$ref);
  if (field.oneOf) {
    const kind = state.preset.look.kind;
    return field.oneOf.map((variant) => definition(variant.$ref)).find((table) => table.properties.kind.const === kind);
  }
  return null;
}

function fieldsOfSection(keys) {
  const fields = [];
  for (const key of keys) {
    const table = tableSchema(key);
    if (!table) {
      fields.push({ key, schema: state.schema.properties[key] });
      continue;
    }
    for (const [name, schema] of Object.entries(table.properties)) fields.push({ key: `${key}.${name}`, schema });
  }
  return fields;
}

function getValue(key) {
  return key.split(".").reduce((value, part) => value?.[part], state.preset);
}

function setValue(key, value) {
  const parts = key.split(".");
  const last = parts.pop();
  parts.reduce((table, part) => table[part], state.preset)[last] = value;
  scheduleUpdate();
}

function bounds(schema) {
  const low = schema.minimum ?? schema.exclusiveMinimum;
  const high = schema.maximum ?? schema.exclusiveMaximum;
  return low !== undefined && high !== undefined ? [low, high] : null;
}

function parseNumber(text, integer) {
  const trimmed = text.trim().toLowerCase();
  if (trimmed === "inf" || trimmed === "infinity") return "Infinity";
  const value = Number(trimmed);
  if (trimmed === "" || Number.isNaN(value)) return text;
  return integer ? Math.round(value) : value;
}

function formatNumber(value) {
  return value === "Infinity" ? "inf" : String(value);
}

function element(tag, attributes = {}, children = []) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === "text") node.textContent = value;
    else node.setAttribute(name, value);
  }
  node.append(...children);
  return node;
}

function numberControl(key, schema) {
  const integer = schema.type === "integer";
  const text = element("input", { type: "text", inputmode: "decimal", id: `field-${key}` });
  text.value = formatNumber(getValue(key));
  const controls = [text];
  const range = bounds(schema);
  if (range && Number.isFinite(range[0]) && Number.isFinite(range[1])) {
    const span = range[1] - range[0];
    const slider = element("input", {
      type: "range", min: range[0], max: range[1], step: integer ? 1 : span <= 2 ? 0.01 : span <= 50 ? 0.1 : 1,
      "aria-labelledby": `label-${key}`,
    });
    slider.value = getValue(key);
    slider.addEventListener("input", () => {
      text.value = slider.value;
      setValue(key, integer ? Math.round(Number(slider.value)) : Number(slider.value));
    });
    text.addEventListener("change", () => (slider.value = text.value));
    controls.unshift(slider);
  }
  text.addEventListener("change", () => setValue(key, parseNumber(text.value, integer)));
  return element("div", { class: "controls" }, controls);
}

function colorsControl(key) {
  const box = element("div", { class: "colors", id: `field-${key}` });
  const draw = () => {
    box.replaceChildren();
    getValue(key).forEach((color, index) => {
      const picker = element("input", { type: "color", "aria-label": `${keyText(key).label} ${index + 1}` });
      picker.value = color.toLowerCase();
      picker.addEventListener("input", () => {
        const colors = [...getValue(key)];
        colors[index] = picker.value.toUpperCase();
        setValue(key, colors);
      });
      const remove = element("button", { type: "button", class: "small", text: t("colors.remove") });
      remove.addEventListener("click", () => {
        setValue(key, getValue(key).filter((_, other) => other !== index));
        draw();
      });
      box.append(picker, remove);
    });
    const add = element("button", { type: "button", class: "small", text: t("colors.add") });
    add.addEventListener("click", () => {
      const colors = getValue(key);
      setValue(key, [...colors, colors.at(-1) ?? "#FFFFFF"]);
      draw();
    });
    box.append(add);
  };
  draw();
  return box;
}

function control(key, schema) {
  const value = getValue(key);
  if (schema.const !== undefined) return element("span", { text: String(value) });
  if (schema.enum) {
    const select = element("select", { id: `field-${key}` }, schema.enum.map((option) => element("option", { text: option })));
    select.value = value;
    select.addEventListener("change", () => setValue(key, select.value));
    return select;
  }
  if (schema.type === "boolean") {
    const box = element("input", { type: "checkbox", id: `field-${key}` });
    box.checked = value;
    box.addEventListener("change", () => setValue(key, box.checked));
    return box;
  }
  if (schema.format === "color") {
    const picker = element("input", { type: "color", id: `field-${key}` });
    picker.value = value.toLowerCase();
    picker.addEventListener("input", () => setValue(key, picker.value.toUpperCase()));
    return picker;
  }
  if (schema.type === "array" && schema.items?.format === "color") return colorsControl(key);
  if (schema.type === "array" && schema.prefixItems) {
    const inputs = value.map((item, index) => {
      const input = element("input", { type: "text", inputmode: "decimal", "aria-label": `${keyText(key).label} ${index + 1}` });
      input.value = formatNumber(item);
      input.addEventListener("change", () => {
        const items = [...getValue(key)];
        items[index] = parseNumber(input.value, false);
        setValue(key, items);
      });
      return input;
    });
    return element("div", { class: "controls triple", id: `field-${key}` }, inputs);
  }
  if (schema.type === "integer" || schema.type === "number") return numberControl(key, schema);
  const input = element("input", { type: "text", id: `field-${key}` });
  input.value = value;
  input.addEventListener("change", () => setValue(key, input.value));
  return input;
}

function field(key, schema) {
  const { label, help } = keyText(key);
  const row = element("div", { class: "field" }, [
    element("label", { id: `label-${key}`, for: `field-${key}`, text: label }),
    control(key, schema),
  ]);
  if (help) row.append(element("span", { class: "help", text: help }));
  state.fields.set(key, row);
  return row;
}

function buildForm() {
  state.fields.clear();
  const open = new Set([...document.querySelectorAll("#sections details[open]")].map((node) => node.dataset.section));
  const sections = SECTIONS.map(([name, keys]) => {
    const details = element("details", { "data-section": name }, [element("summary", { text: t(`section.${name}`) })]);
    if (open.has(name) || (open.size === 0 && name !== "analysis")) details.open = true;
    for (const { key, schema } of fieldsOfSection(keys)) {
      if (!HIDDEN_KEYS.has(key)) details.append(field(key, schema));
    }
    return details;
  });
  $("sections").replaceChildren(...sections);
  $("name-field").replaceChildren(field("name", state.schema.properties.name));
}

function showProblems(errors) {
  for (const row of state.fields.values()) {
    row.classList.remove("invalid");
    row.querySelector(".problem")?.remove();
  }
  const general = [];
  for (const { key, message } of errors) {
    // Validation names the look variant ("look.flat.max_height"); the form uses "look.max_height".
    const formKey = key.replace(/^look\.(flat|perspective)\./, "look.");
    const row = state.fields.get(formKey);
    if (row) {
      row.classList.add("invalid");
      row.append(element("span", { class: "problem", text: message }));
    } else {
      general.push(`${key || "preset"}: ${message}`);
    }
  }
  return general;
}

// --- Song, output and preview ------------------------------------------------------------------------------------

function output() {
  const [width, height] = $("size").value.split("x").map(Number);
  const transparent = $("format").value === "prores4444" && $("transparent").checked;
  return { width, height, fps: Number($("fps").value), transparent };
}

function formatDuration(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

function showSong() {
  $("song-info").textContent = state.song ? `${state.song.name} (${formatDuration(state.song.duration)})` : t("song.none");
}

async function openSong(path) {
  if (!path) return;
  try {
    state.song = await (await api("/api/song", { path, fps: output().fps })).json();
    $("song-path").value = state.song.path;
    const last = Math.max(0, state.song.duration - 0.1).toFixed(1);
    for (const input of [$("time-range"), $("time")]) {
      input.max = last;
      input.disabled = false;
    }
    if (Number($("time").value) > Number(last) || Number($("time").value) === 0) {
      $("time").value = $("time-range").value = Math.min(30, Number(last) / 2).toFixed(1);
    }
    $("play-clip").disabled = false;
    $("start-render").disabled = state.renderTimer !== null;
    showSong();
    showError(null);
    scheduleUpdate();
  } catch (error) {
    showError(error);
  }
}

function scheduleUpdate() {
  clearTimeout(state.timer);
  state.timer = setTimeout(updatePreview, UPDATE_DELAY_MS);
}

// Checks the settings, shows warnings, then the still. Responses to older requests are ignored.
async function updatePreview() {
  const request = ++state.previewRequest;
  const preset = structuredClone(state.preset);
  $("frame").classList.toggle("transparent", output().transparent);
  try {
    const { warnings } = await (await api("/api/warnings", preset)).json();
    if (request !== state.previewRequest) return;
    showProblems([]);
    $("warning-list").replaceChildren(...warnings.map((text) => element("li", { text })));
    $("warnings").hidden = warnings.length === 0;
    showError(null);
  } catch (error) {
    if (request !== state.previewRequest) return;
    if (error.code === "preset_invalid") {
      const general = showProblems(error.errors);
      error.message = general.join("\n");
    }
    showError(error);
    return;
  }
  if (!state.song) return;
  $("preview-status").textContent = t("preview.updating");
  try {
    const { width, height, transparent } = output();
    const time = Number($("time").value);
    const image = await (await api("/api/still", { preset, time, width, height, transparent })).blob();
    if (request !== state.previewRequest) return;
    if (state.stillUrl) URL.revokeObjectURL(state.stillUrl);
    state.stillUrl = URL.createObjectURL(image);
    $("still").src = state.stillUrl;
    $("still").hidden = false;
    $("clip").hidden = true;
    $("preview-empty").hidden = true;
    $("preview-status").textContent = "";
  } catch (error) {
    if (request === state.previewRequest) {
      $("preview-status").textContent = "";
      showError(error);
    }
  }
}

async function playClip() {
  const { width, height, transparent } = output();
  $("play-clip").disabled = true;
  $("preview-status").textContent = t("preview.clip_rendering");
  try {
    const body = { preset: state.preset, start: Number($("time").value), width, height };
    const video = await (await api("/api/clip", body)).blob();
    if (state.clipUrl) URL.revokeObjectURL(state.clipUrl);
    state.clipUrl = URL.createObjectURL(video);
    $("clip").src = state.clipUrl;
    $("clip").hidden = false;
    $("still").hidden = true;
    $("frame").classList.remove("transparent");
    $("preview-status").textContent = transparent ? t("preview.clip_opaque") : "";
    await $("clip").play().catch(() => {});
  } catch (error) {
    $("preview-status").textContent = "";
    showError(error);
  } finally {
    $("play-clip").disabled = false;
  }
}

// --- Presets and rendering ---------------------------------------------------------------------------------------

async function refreshPresets(selected) {
  const { builtin, user, shadowed } = await (await api("/api/presets")).json();
  const group = (label, names) =>
    element("optgroup", { label }, names.map((name) => element("option", { value: name, text: name })));
  const groups = [group(t("preset.builtin_group"), builtin)];
  if (user.length) groups.push(group(t("preset.user_group"), user));
  $("builtin").replaceChildren(...groups);
  $("builtin").value = selected;
  $("preset-status").textContent = shadowed.length ? t("preset.shadowed", { names: shadowed.join(", ") }) : "";
}

async function savePreset() {
  const save = (overwrite) => api("/api/presets", { preset: state.preset, overwrite });
  try {
    let response;
    try {
      response = await save(false);
    } catch (error) {
      if (error.code !== "output_exists" || !confirm(t("preset.overwrite", { name: state.preset.name }))) throw error;
      response = await save(true);
    }
    const { name, path } = await response.json();
    await refreshPresets(name);
    $("preset-status").textContent = t("preset.saved", { path });
    showError(null);
  } catch (error) {
    showError(error);
  }
}

function showFolder() {
  $("output-folder").textContent = state.outputDir ?? t("render.next_to_song");
}

async function chooseFolder() {
  try {
    const { path } = await (await api("/api/dialogs/folder", { prompt: t("render.folder_prompt") })).json();
    if (path) state.outputDir = path;
    showFolder();
  } catch (error) {
    showError(error);
  }
}

async function startRender() {
  const { width, height, fps, transparent } = output();
  const body = {
    preset: state.preset, output_dir: state.outputDir, width, height, fps, format: $("format").value, transparent,
  };
  try {
    try {
      await api("/api/render", { ...body, overwrite: false });
    } catch (error) {
      if (error.code !== "output_exists" || !confirm(t("render.overwrite", { output: error.detail.output }))) throw error;
      await api("/api/render", { ...body, overwrite: true });
    }
    showError(null);
    showRendering(true);
    state.renderTimer = setInterval(pollRender, RENDER_POLL_MS);
  } catch (error) {
    showError(error);
  }
}

function showRendering(running) {
  $("start-render").disabled = running || !state.song;
  $("cancel-render").hidden = !running;
  $("render-progress").hidden = !running;
  if (running) $("reveal").hidden = true;
}

async function pollRender() {
  let status;
  try {
    status = await (await api("/api/render")).json();
  } catch (error) {
    showError(error);
    return;
  }
  const { state: phase, frame, frames, output: path, seconds, error } = status;
  if (phase === "running") {
    $("render-progress").max = frames || 1;
    $("render-progress").value = frame;
    const percent = frames ? Math.floor((frame * 100) / frames) : 0;
    $("render-status").textContent = frames ? t("render.progress", { frame, frames, percent }) : "";
    return;
  }
  clearInterval(state.renderTimer);
  state.renderTimer = null;
  showRendering(false);
  if (phase === "done") {
    $("render-status").textContent = t("render.done", { seconds: seconds.toFixed(1), output: path });
    $("reveal").hidden = false;
  } else if (phase === "cancelled") {
    $("render-status").textContent = t("render.cancelled");
  } else if (phase === "failed") {
    $("render-status").textContent = "";
    showError(new ApiError(500, error));
  }
}

async function loadBuiltin(name) {
  try {
    state.preset = await (await api(`/api/presets/${name}`)).json();
    buildForm();
    scheduleUpdate();
  } catch (error) {
    showError(error);
  }
}

// --- Start -------------------------------------------------------------------------------------------------------

function wire() {
  $("language").replaceChildren(
    ...Object.entries(LANGUAGES).map(([code, name]) => element("option", { value: code, text: name })),
  );
  $("language").value = state.language;
  $("language").addEventListener("change", () => {
    rememberLanguage($("language").value);
    setLanguage($("language").value).catch(showError);
  });
  $("open-song").addEventListener("click", async () => {
    try {
      const { path } = await (await api("/api/dialogs/audio", { prompt: t("song.prompt") })).json();
      await openSong(path);
    } catch (error) {
      showError(error);
    }
  });
  $("song-path").addEventListener("keydown", (event) => {
    if (event.key === "Enter") openSong($("song-path").value.trim());
  });
  $("builtin").addEventListener("change", () => loadBuiltin($("builtin").value));
  $("time-range").addEventListener("input", () => {
    $("time").value = $("time-range").value;
    scheduleUpdate();
  });
  $("time").addEventListener("change", () => {
    $("time-range").value = $("time").value;
    scheduleUpdate();
  });
  $("format").addEventListener("change", () => {
    $("transparent").disabled = $("format").value !== "prores4444";
    scheduleUpdate();
  });
  $("transparent").addEventListener("change", scheduleUpdate);
  $("size").addEventListener("change", scheduleUpdate);
  // The frame rate changes the analysis, so the song is opened again with it.
  $("fps").addEventListener("change", () => (state.song ? openSong(state.song.path) : null));
  $("play-clip").addEventListener("click", playClip);
  $("save-preset").addEventListener("click", savePreset);
  $("choose-folder").addEventListener("click", chooseFolder);
  $("start-render").addEventListener("click", startRender);
  $("cancel-render").addEventListener("click", () => api("/api/render/cancel", {}).catch(showError));
  $("reveal").addEventListener("click", () => api("/api/reveal", {}).catch(showError));
}

async function start() {
  const params = new URLSearchParams(location.search);
  if (params.has("token")) {
    sessionStorage.setItem("token", params.get("token"));
    history.replaceState(null, "", location.pathname);
  }
  state.token = sessionStorage.getItem("token");
  const stored = storedLanguage();
  state.language = stored in LANGUAGES ? stored : browserLanguage();
  wire();
  await setLanguage(state.language);
  try {
    state.schema = await (await api("/api/schema")).json();
    await refreshPresets("default");
    await loadBuiltin("default");
  } catch (error) {
    showError(error);
  }
}

start();
