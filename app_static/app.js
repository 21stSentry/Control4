const $ = (id) => document.getElementById(id);

let config = null;
const THEME_KEY = "matrix_theme";
const ioTest = {
  steps: [],
  index: -1,
  results: [],
  running: false,
};

function setPresetState(text) {
  $("presetState").textContent = text || "";
}

function setRoutingStatus(text) {
  $("routingStatus").textContent = text || "";
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return res.json();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function renderZones() {
  const grid = $("zonesGrid");
  grid.innerHTML = "";
  const zones = config.zones || {};
  Object.keys(zones)
    .sort((a, b) => Number(a) - Number(b))
    .forEach((zone) => {
      const card = document.createElement("div");
      card.className = "zone";

      const label = document.createElement("div");
      label.textContent = `Zone ${zone}`;

      const select = document.createElement("select");
      for (let s = 1; s <= 16; s += 1) {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = `Source ${s}`;
        if (Number(zones[zone]) === s) opt.selected = true;
        select.appendChild(opt);
      }

      select.addEventListener("change", async () => {
        config.zones[zone] = Number(select.value);
        const body = {
          zone,
          source: Number(select.value),
          host: $("host").value,
          port: Number($("port").value),
          bind_ip: $("bindIp").value.trim(),
        };
        const out = await api("/api/route", {
          method: "POST",
          body: JSON.stringify(body),
        });
        $("telnetOutput").textContent = JSON.stringify(out, null, 2);
      });

      card.append(label, select);
      grid.appendChild(card);
    });
}

function renderPresets() {
  const holder = $("presets");
  holder.innerHTML = "";
  const presets = config.presets || {};
  Object.keys(presets).forEach((name) => {
    const btn = document.createElement("button");
    btn.textContent = name;
    btn.addEventListener("click", async () => {
      const out = await api("/api/preset/apply", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (out.ok) {
        config.zones = out.zones;
        renderZones();
        setPresetState(`Loaded preset: ${name}. Click "Apply to Unit" to push.`);
      }
    });
    holder.appendChild(btn);
  });
}

function renderPresetManager() {
  const select = $("presetSelect");
  const defaultSelect = $("defaultPresetSelect");
  const names = Object.keys(config.presets || {});
  select.innerHTML = "";
  defaultSelect.innerHTML = "";

  names.forEach((name) => {
    const opt1 = document.createElement("option");
    opt1.value = name;
    opt1.textContent = name;
    select.appendChild(opt1);

    const opt2 = document.createElement("option");
    opt2.value = name;
    opt2.textContent = name;
    defaultSelect.appendChild(opt2);
  });

  if (config.default_preset && names.includes(config.default_preset)) {
    defaultSelect.value = config.default_preset;
  } else if (names.length > 0) {
    config.default_preset = names[0];
    defaultSelect.value = names[0];
  }
  $("autoApplyDefaultPreset").checked = Boolean(config.auto_apply_default_preset);
}

async function refreshStatus() {
  const host = $("host").value;
  const port = $("port").value;
  const bindIp = $("bindIp").value.trim();
  const out = await api(
    `/api/status?host=${encodeURIComponent(host)}&port=${encodeURIComponent(port)}&bind_ip=${encodeURIComponent(bindIp)}`
  );
  $("statusOutput").textContent = JSON.stringify(out, null, 2);
}

async function saveConfig() {
  config.device.host = $("host").value;
  config.device.port = Number($("port").value);
  config.device.bind_ip = $("bindIp").value.trim();
  config.default_preset = $("defaultPresetSelect").value || config.default_preset || "";
  config.auto_apply_default_preset = $("autoApplyDefaultPreset").checked;
  const out = await api("/api/config", {
    method: "POST",
    body: JSON.stringify({ config }),
  });
  $("saveState").textContent = out.ok ? "Saved" : `Save failed: ${out.error || "unknown"}`;
  setTimeout(() => {
    $("saveState").textContent = "";
  }, 2000);
}

async function savePresetConfig(message) {
  await saveConfig();
  setPresetState(message);
}

async function addPreset() {
  const name = $("presetName").value.trim();
  if (!name) {
    setPresetState("Enter a preset name first.");
    return;
  }
  config.presets = config.presets || {};
  config.presets[name] = { ...config.zones };
  $("presetName").value = "";
  renderPresets();
  renderPresetManager();
  await savePresetConfig(`Saved preset: ${name}`);
}

async function renamePreset() {
  const oldName = $("presetSelect").value;
  const newName = $("renamePresetName").value.trim();
  if (!oldName) {
    setPresetState("Select a preset to rename.");
    return;
  }
  if (!newName) {
    setPresetState("Enter a new preset name.");
    return;
  }
  if (oldName === newName) {
    setPresetState("New name is the same as current name.");
    return;
  }
  const preset = config.presets[oldName];
  delete config.presets[oldName];
  config.presets[newName] = preset;
  if (config.default_preset === oldName) {
    config.default_preset = newName;
  }
  $("renamePresetName").value = "";
  renderPresets();
  renderPresetManager();
  await savePresetConfig(`Renamed preset: ${oldName} -> ${newName}`);
}

async function deletePreset() {
  const name = $("presetSelect").value;
  if (!name) {
    setPresetState("Select a preset to delete.");
    return;
  }
  delete config.presets[name];
  const remaining = Object.keys(config.presets);
  if (config.default_preset === name) {
    config.default_preset = remaining[0] || "";
  }
  renderPresets();
  renderPresetManager();
  await savePresetConfig(`Deleted preset: ${name}`);
}

async function sendRaw() {
  const command = $("telnetCommand").value.trim();
  if (!command) return;
  const body = {
    command,
    host: $("host").value,
    port: Number($("port").value),
    bind_ip: $("bindIp").value.trim(),
  };
  const out = await api("/api/telnet/send", {
    method: "POST",
    body: JSON.stringify(body),
  });
  $("telnetOutput").textContent = JSON.stringify(out, null, 2);
}

async function applyCurrentRoutingToUnit() {
  const applyBtn = $("applyToUnit");
  const originalLabel = applyBtn.textContent;
  applyBtn.disabled = true;
  applyBtn.textContent = "Applying...";

  try {
  const zones = config.zones || {};
  const zoneIds = Object.keys(zones).sort((a, b) => Number(a) - Number(b));
  if (zoneIds.length === 0) {
    setPresetState("No zone routing loaded.");
    setRoutingStatus("No apply run yet.");
    return;
  }
  const startedAt = new Date().toISOString();
  let okCount = 0;
  let failCount = 0;
  const results = [];
  for (const zone of zoneIds) {
    const source = Number(zones[zone]);
    try {
      let out = null;
      let attempts = 0;
      const maxAttempts = 3;
      while (attempts < maxAttempts) {
        attempts += 1;
        out = await api("/api/route", {
          method: "POST",
          body: JSON.stringify({
            zone,
            source,
            host: $("host").value,
            port: Number($("port").value),
            bind_ip: $("bindIp").value.trim(),
          }),
        });
        if (out.ok && out.applied) break;
        const responseText = String(out.device_response || out.error || "");
        const retryable = responseText.includes("Errno 61") || responseText.toLowerCase().includes("refused");
        if (!retryable || attempts >= maxAttempts) break;
        await sleep(220 * attempts);
      }
      if (out.ok && out.applied) {
        okCount += 1;
      } else {
        failCount += 1;
      }
      results.push({
        zone,
        source,
        ok: Boolean(out.ok),
        applied: Boolean(out.applied),
        command: out.command || "",
        note: out.note || "",
        device_response: out.device_response || "",
        attempts,
      });
    } catch (err) {
      failCount += 1;
      results.push({
        zone,
        source,
        ok: false,
        applied: false,
        error: String(err),
      });
    }
  }
  const completedAt = new Date().toISOString();
  const failed = results.filter((r) => !r.ok || !r.applied);
  const bindIp = $("bindIp").value.trim();
  const hints = [];
  if (failed.length > 0 && !bindIp) {
    hints.push("Set Local Bind IP if using direct Ethernet + Wi-Fi at the same time.");
  }
  if (failed.length > 0) {
    hints.push("Check device host/port and confirm Telnet port 23 is reachable.");
  }
  setRoutingStatus(
    JSON.stringify(
      {
        started_at: startedAt,
        completed_at: completedAt,
        host: $("host").value,
        port: Number($("port").value),
        bind_ip: bindIp,
        total: zoneIds.length,
        ok: okCount,
        failed: failCount,
        failures: failed,
        hints,
      },
      null,
      2
    )
  );
  if (failCount === 0) {
    setPresetState(`Applied to unit successfully: ${okCount}/${zoneIds.length} zones.`);
  } else {
    setPresetState(
      `Apply completed with errors: ok=${okCount}, failed=${failCount}. See Routing Status for details.`
    );
    $("telnetOutput").textContent = JSON.stringify(failed, null, 2);
  }
  } finally {
    applyBtn.disabled = false;
    applyBtn.textContent = originalLabel;
  }
}

function buildIoSteps() {
  const steps = [];
  for (let source = 1; source <= 16; source += 1) {
    for (let zone = 1; zone <= 16; zone += 1) {
      steps.push({ source, zone });
    }
  }
  return steps;
}

async function applyIoStep(step) {
  const out = await api("/api/route", {
    method: "POST",
    body: JSON.stringify({
      zone: String(step.zone),
      source: step.source,
      host: $("host").value,
      port: Number($("port").value),
      bind_ip: $("bindIp").value.trim(),
    }),
  });
  return out;
}

function ioSummary() {
  const total = ioTest.steps.length || 0;
  const done = ioTest.results.length;
  const pass = ioTest.results.filter((r) => r.result === "PASS").length;
  const fail = ioTest.results.filter((r) => r.result === "FAIL").length;
  const skip = ioTest.results.filter((r) => r.result === "SKIP").length;
  return { total, done, pass, fail, skip };
}

function renderIoState(extra = "") {
  const summary = ioSummary();
  if (!ioTest.running && ioTest.index < 0) {
    $("ioState").textContent = "Not started.";
    return;
  }
  if (!ioTest.running && summary.done === summary.total && summary.total > 0) {
    $("ioState").textContent =
      `Completed ${summary.done}/${summary.total}\nPASS: ${summary.pass}  FAIL: ${summary.fail}  SKIP: ${summary.skip}\n` +
      JSON.stringify(ioTest.results, null, 2);
    return;
  }
  const current = ioTest.steps[ioTest.index];
  $("ioState").textContent =
    `Step ${ioTest.index + 1}/${summary.total}\n` +
    `Route Source ${current.source} -> Zone ${current.zone}\n` +
    `Completed: ${summary.done} | PASS: ${summary.pass} FAIL: ${summary.fail} SKIP: ${summary.skip}\n` +
    (extra ? `\n${extra}` : "");
}

async function startIoTest() {
  ioTest.steps = buildIoSteps();
  ioTest.index = 0;
  ioTest.results = [];
  ioTest.running = true;
  const out = await applyIoStep(ioTest.steps[ioTest.index]);
  renderIoState(`Device command sent. applied=${out.applied}`);
}

function resetIoTest() {
  ioTest.steps = [];
  ioTest.index = -1;
  ioTest.results = [];
  ioTest.running = false;
  renderIoState();
}

async function markIo(result) {
  if (!ioTest.running || ioTest.index < 0 || ioTest.index >= ioTest.steps.length) return;
  const step = ioTest.steps[ioTest.index];
  ioTest.results.push({ ...step, result });
  ioTest.index += 1;
  if (ioTest.index >= ioTest.steps.length) {
    ioTest.running = false;
    renderIoState();
    return;
  }
  const out = await applyIoStep(ioTest.steps[ioTest.index]);
  renderIoState(`Device command sent. applied=${out.applied}`);
}

async function init() {
  const savedTheme = localStorage.getItem(THEME_KEY) || "dark";
  document.body.classList.toggle("dark", savedTheme === "dark");
  $("themeToggle").textContent = savedTheme === "dark" ? "Light Mode" : "Dark Mode";

  const out = await api("/api/config");
  config = out.config;
  config.presets = config.presets || {};
  config.default_preset = config.default_preset || "";
  config.auto_apply_default_preset = Boolean(config.auto_apply_default_preset);
  $("host").value = config.device.host;
  $("port").value = config.device.port;
  $("bindIp").value = config.device.bind_ip || "";
  renderZones();
  renderPresets();
  renderPresetManager();
  refreshStatus();
  renderIoState();
  setPresetState("");
  setRoutingStatus("No apply run yet.");

  if (config.auto_apply_default_preset && config.default_preset && config.presets[config.default_preset]) {
    const outPreset = await api("/api/preset/apply", {
      method: "POST",
      body: JSON.stringify({ name: config.default_preset }),
    });
    if (outPreset.ok && outPreset.zones) {
      config.zones = outPreset.zones;
      renderZones();
      setPresetState(`Auto-loaded default preset: ${config.default_preset}. Click "Apply to Unit" to push.`);
    }
  }
}

function toggleTheme() {
  const nowDark = !document.body.classList.contains("dark");
  document.body.classList.toggle("dark", nowDark);
  localStorage.setItem(THEME_KEY, nowDark ? "dark" : "light");
  $("themeToggle").textContent = nowDark ? "Light Mode" : "Dark Mode";
}

$("refreshStatus").addEventListener("click", refreshStatus);
$("saveConfig").addEventListener("click", saveConfig);
$("sendTelnet").addEventListener("click", sendRaw);
$("themeToggle").addEventListener("click", toggleTheme);
$("startIoTest").addEventListener("click", startIoTest);
$("ioPass").addEventListener("click", () => markIo("PASS"));
$("ioFail").addEventListener("click", () => markIo("FAIL"));
$("ioSkip").addEventListener("click", () => markIo("SKIP"));
$("resetIoTest").addEventListener("click", resetIoTest);
$("addPreset").addEventListener("click", addPreset);
$("renamePreset").addEventListener("click", renamePreset);
$("deletePreset").addEventListener("click", deletePreset);
$("applyToUnit").addEventListener("click", applyCurrentRoutingToUnit);
$("defaultPresetSelect").addEventListener("change", async () => {
  config.default_preset = $("defaultPresetSelect").value;
  await savePresetConfig(`Default preset set: ${config.default_preset}`);
});
$("autoApplyDefaultPreset").addEventListener("change", async () => {
  config.auto_apply_default_preset = $("autoApplyDefaultPreset").checked;
  await savePresetConfig(
    config.auto_apply_default_preset
      ? "Auto-apply default preset is ON."
      : "Auto-apply default preset is OFF."
  );
});

init();
