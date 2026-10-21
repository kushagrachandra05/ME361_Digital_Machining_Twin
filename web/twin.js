/**
 * ME361 Digital Machining Twin - Core Engine & Visualizers
 * Strictly preserves locked scope: pure orthogonal, single shear plane, steady state.
 */

// --- CALIBRATED PRESETS ---
const PRESETS = {
  "SS316L": {
    name: "SS316L (Provisional Calibrated)",
    material: "SS316L",
    tau_s: 176.09, // 305 / sqrt(3) MPa initial yield
    sigma_y: 305.0,
    mu: 0.877,
    tau_k: 5.439, // accounts for severe work-hardening at shear strain ~2
    gamma0_deg: 0.0,
    w: 2.0,
    Vc: 125,
    t: 0.10,
    corrections: {
      Ke_z: 13.23,
      Ke_xy: 0.0,
      n_mu: 0.266,
      c_rate: 0.0,
      m_mu: 0.0,
      shear_model: "ernst_merchant"
    },
    meta: "Provisional: JC(A=305,B=1161,n=0.61) at shear strain, edge/friction parameters transferred from Ck45 (uncoated carbide, rn~38um)."
  },
  "Ck45": {
    name: "Ck45 (ETH Zürich 519-Run Fit)",
    material: "Ck45",
    tau_s: 242.49, // 420 / sqrt(3) MPa
    sigma_y: 420.0,
    mu: 0.877,
    tau_k: 2.663,
    gamma0_deg: 0.0,
    w: 1.0,
    Vc: 200,
    t: 0.10,
    corrections: {
      Ke_z: 13.23,
      Ke_xy: 0.0,
      n_mu: 0.266,
      c_rate: 0.0,
      m_mu: 0.0,
      shear_model: "ernst_merchant"
    },
    meta: "Calibrated on 95 in-scope Ck45 cuts from ETH Table B.15 (vc >= 150 m/min, continuous chips, BUE excluded)."
  },
  "Ti6Al4V": {
    name: "Ti6Al4V (ETH Zürich Calibrated)",
    material: "Ti6Al4V",
    tau_s: 501.72, // 869 / sqrt(3) MPa
    sigma_y: 869.0,
    mu: 0.766,
    tau_k: 0.888,
    gamma0_deg: 0.0,
    w: 1.0,
    Vc: 100,
    t: 0.10,
    corrections: {
      Ke_z: 15.34,
      Ke_xy: 0.0,
      n_mu: 0.419,
      c_rate: 0.0,
      m_mu: 0.0,
      shear_model: "ernst_merchant"
    },
    meta: "Calibrated on 273 ETH Ti6Al4V cuts. Note: Ti6Al4V forms segmented chips at all conditions."
  },
  "CUSTOM": {
    name: "Pure Slide Baseline (Custom Inputs)",
    material: "Custom Steel/Alloy",
    tau_s: 300.0,
    sigma_y: 520.0,
    mu: 0.50,
    tau_k: 1.0,
    gamma0_deg: 5.0,
    w: 2.0,
    Vc: 120,
    t: 0.10,
    corrections: {
      Ke_z: 0.0,
      Ke_xy: 0.0,
      n_mu: 0.0,
      c_rate: 0.0,
      m_mu: 0.0,
      shear_model: "ernst_merchant"
    },
    meta: "Uncalibrated baseline pure slide model (all correction factors OFF)."
  }
};

// --- PHYSICS ENGINE ---
function shearAngle(model, gamma0, eta, C_deg = 70.0) {
  if (model === "ernst_merchant") return Math.PI / 4 + gamma0 / 2 - eta / 2;
  if (model === "lee_shaffer") return Math.PI / 4 + gamma0 - eta;
  if (model === "stabler") return Math.PI / 4 + gamma0 / 2 - eta;
  if (model === "merchant_C") return 0.5 * ((C_deg * Math.PI) / 180 - eta + gamma0);
  return Math.PI / 4 + gamma0 / 2 - eta / 2;
}

function solveOrthogonal(params, applyCorrections = true) {
  const g = (params.gamma0_deg * Math.PI) / 180;
  const Vc = Math.max(params.Vc, 1e-9);
  const t = Math.max(params.t, 1e-6);
  const w = Math.max(params.w, 1e-6);

  let tau = params.tau_s * (applyCorrections ? params.tau_k : 1.0);
  let mu = params.mu;
  let Ke_z = 0.0;
  let Ke_xy = 0.0;
  let shear_model = "ernst_merchant";

  if (applyCorrections && params.corrections) {
    const c_rate = params.corrections.c_rate || 0.0;
    const m_mu = params.corrections.m_mu || 0.0;
    const n_mu = params.corrections.n_mu || 0.0;
    const Vref = 100.0;
    const t_ref = 0.1;

    tau *= (1.0 + c_rate * Math.log(Vc / Vref));
    mu = params.mu * Math.pow(Vc / Vref, -m_mu) * Math.pow(t / t_ref, -n_mu);
    Ke_z = params.corrections.Ke_z || 0.0;
    Ke_xy = params.corrections.Ke_xy || 0.0;
    shear_model = params.corrections.shear_model || "ernst_merchant";
  }

  const eta = Math.atan(mu);
  const beta = shearAngle(shear_model, g, eta);

  if (beta <= 0 || beta >= Math.PI / 2 || beta + eta - g >= Math.PI / 2) {
    return { valid: false, error: "Non-physical shear angle" };
  }

  const A_shear = (w * t) / Math.sin(beta);
  const Ps = tau * A_shear;
  const R_shear = Ps / Math.cos(beta + eta - g);

  const Pz = R_shear * Math.cos(eta - g) + Ke_z * w;
  const Pxy = R_shear * Math.sin(eta - g) + Ke_xy * w;
  const R = Math.hypot(Pz, Pxy);

  const F = Pz * Math.sin(g) + Pxy * Math.cos(g);
  const N = Pz * Math.cos(g) - Pxy * Math.sin(g);
  const PN = Pz * Math.sin(beta) + Pxy * Math.cos(beta);
  const Ps_chk = Pz * Math.cos(beta) - Pxy * Math.sin(beta);

  const r = Math.sin(beta) / Math.cos(beta - g);
  const t_chip = t / r;
  const Vc_ms = Vc / 60.0;
  const V_chip = Vc_ms * r;
  const V_shear = (Vc_ms * Math.cos(g)) / Math.cos(beta - g);

  return {
    valid: true,
    beta_rad: beta,
    beta_deg: (beta * 180) / Math.PI,
    eta_rad: eta,
    eta_deg: (eta * 180) / Math.PI,
    gamma0_deg: params.gamma0_deg,
    gamma0_rad: g,
    mu_eff: mu,
    tau_eff: tau,
    Ps: Ps_chk,
    PN,
    F,
    N,
    R,
    Pz,
    Pxy,
    r,
    t_chip,
    V_chip,
    V_shear,
    Kc: Pz / (w * t),
    Kf: Pxy / (w * t),
    Ke_z,
    Ke_xy
  };
}

// --- APP STATE & UI WIRING ---
const state = {
  presetKey: "SS316L",
  materialName: "SS316L",
  Vc: 125,
  t: 0.10,
  w: 2.0,
  gamma0_deg: 0.0,
  tau_s: 176.09,
  sigma_y: 305.0,
  mu: 0.877,
  tau_k: 5.439,
  corrections: {
    Ke_z: 13.23,
    Ke_xy: 0.0,
    n_mu: 0.266,
    c_rate: 0.0,
    m_mu: 0.0,
    shear_model: "ernst_merchant"
  },
  useCorrections: true,
  showBaseline: true,
  simTime: 0,
  isRunning: true,
  simSpeed: 1.0,
  logHistory: [],
  maxLogRows: 150,
  chartHistory: {
    time: [],
    Pz_corr: [],
    Pxy_corr: [],
    Pz_base: [],
    Pxy_base: []
  }
};

// DOM references
const elements = {};

function initDOM() {
  const ids = [
    "presetSelect", "paramVc", "valVc", "paramT", "valT", "paramW", "valW",
    "paramGamma", "valGamma", "paramTauS", "valTauS", "paramSigmaY", "valSigmaY",
    "paramMu", "valMu", "toggleCorrections", "toggleBaseline", "btnPlayPause",
    "btnReset", "btnExportCSV", "btnOpenAssumptions", "btnCloseAssumptions",
    "assumptionsModal", "canvasAnim", "canvasCircle", "canvasChart",
    "statPz", "statPxy", "statR", "statBeta", "statEta", "statChip", "statKc",
    "deltaPz", "deltaPxy", "telemetryTableBody", "presetMetaNote"
  ];
  ids.forEach(id => { elements[id] = document.getElementById(id); });

  // Event Listeners
  elements.presetSelect.addEventListener("change", e => applyPreset(e.target.value));
  
  const bindSlider = (slider, valDisp, stateKey, unit = "", multiplier = 1, isFloat = true) => {
    slider.addEventListener("input", e => {
      const v = isFloat ? parseFloat(e.target.value) : parseInt(e.target.value, 10);
      state[stateKey] = v;
      valDisp.textContent = `${(v * multiplier).toFixed(isFloat ? 2 : 0)}${unit}`;
      recalculate();
    });
  };

  bindSlider(elements.paramVc, elements.valVc, "Vc", " m/min", 1, false);
  bindSlider(elements.paramT, elements.valT, "t", " mm", 1, true);
  bindSlider(elements.paramW, elements.valW, "w", " mm", 1, true);
  bindSlider(elements.paramGamma, elements.valGamma, "gamma0_deg", "°", 1, false);
  bindSlider(elements.paramTauS, elements.valTauS, "tau_s", " MPa", 1, false);
  bindSlider(elements.paramMu, elements.valMu, "mu", "", 1, true);

  elements.toggleCorrections.addEventListener("change", e => {
    state.useCorrections = e.target.checked;
    recalculate();
  });

  elements.toggleBaseline.addEventListener("change", e => {
    state.showBaseline = e.target.checked;
    recalculate();
  });

  elements.btnPlayPause.addEventListener("click", () => {
    state.isRunning = !state.isRunning;
    elements.btnPlayPause.textContent = state.isRunning ? "Pause" : "Resume";
  });

  elements.btnReset.addEventListener("click", () => {
    state.simTime = 0;
    state.logHistory = [];
    state.chartHistory = { time: [], Pz_corr: [], Pxy_corr: [], Pz_base: [], Pxy_base: [] };
    updateTelemetryTable();
  });

  elements.btnExportCSV.addEventListener("click", exportLogCSV);

  elements.btnOpenAssumptions.addEventListener("click", () => {
    elements.assumptionsModal.classList.add("active");
  });

  elements.btnCloseAssumptions.addEventListener("click", () => {
    elements.assumptionsModal.classList.remove("active");
  });

  elements.assumptionsModal.addEventListener("click", e => {
    if (e.target === elements.assumptionsModal) {
      elements.assumptionsModal.classList.remove("active");
    }
  });

  // Apply default preset
  applyPreset("SS316L");
  setupCanvases();
  requestAnimationFrame(animationLoop);
}

function applyPreset(key) {
  const p = PRESETS[key];
  if (!p) return;
  state.presetKey = key;
  state.materialName = p.material;
  state.Vc = p.Vc;
  state.t = p.t;
  state.w = p.w;
  state.gamma0_deg = p.gamma0_deg;
  state.tau_s = p.tau_s;
  state.sigma_y = p.sigma_y;
  state.mu = p.mu;
  state.tau_k = p.tau_k;
  state.corrections = { ...p.corrections };

  // Update UI values
  elements.presetSelect.value = key;
  elements.paramVc.value = state.Vc;
  elements.valVc.textContent = `${state.Vc} m/min`;
  elements.paramT.value = state.t;
  elements.valT.textContent = `${state.t.toFixed(2)} mm`;
  elements.paramW.value = state.w;
  elements.valW.textContent = `${state.w.toFixed(1)} mm`;
  elements.paramGamma.value = state.gamma0_deg;
  elements.valGamma.textContent = `${state.gamma0_deg}°`;
  elements.paramTauS.value = Math.round(state.tau_s);
  elements.valTauS.textContent = `${Math.round(state.tau_s)} MPa`;
  elements.paramMu.value = state.mu;
  elements.valMu.textContent = state.mu.toFixed(2);
  elements.presetMetaNote.textContent = p.meta;

  recalculate();
}

let activeResult = null;
let baselineResult = null;

function recalculate() {
  activeResult = solveOrthogonal(state, state.useCorrections);
  baselineResult = solveOrthogonal(state, false);

  if (!activeResult.valid) {
    elements.statPz.textContent = "ERR";
    elements.statPxy.textContent = "ERR";
    return;
  }

  // Update Stat Cards
  elements.statPz.textContent = Math.round(activeResult.Pz);
  elements.statPxy.textContent = Math.round(activeResult.Pxy);
  elements.statR.textContent = Math.round(activeResult.R);
  elements.statBeta.textContent = activeResult.beta_deg.toFixed(1);
  elements.statEta.textContent = activeResult.eta_deg.toFixed(1);
  elements.statChip.textContent = activeResult.t_chip.toFixed(3);
  elements.statKc.textContent = Math.round(activeResult.Kc);

  // Delta calculation vs pure slide baseline
  if (state.useCorrections && baselineResult && baselineResult.valid) {
    const dPz = ((activeResult.Pz - baselineResult.Pz) / baselineResult.Pz) * 100;
    const dPxy = ((activeResult.Pxy - baselineResult.Pxy) / baselineResult.Pxy) * 100;

    elements.deltaPz.style.display = "inline-block";
    elements.deltaPxy.style.display = "inline-block";
    elements.deltaPz.textContent = `${dPz >= 0 ? "+" : ""}${dPz.toFixed(1)}% vs Base`;
    elements.deltaPxy.textContent = `${dPxy >= 0 ? "+" : ""}${dPxy.toFixed(1)}% vs Base`;
    elements.deltaPz.className = `metric-delta ${dPz >= 0 ? "delta-plus" : "delta-minus"}`;
    elements.deltaPxy.className = `metric-delta ${dPxy >= 0 ? "delta-plus" : "delta-minus"}`;
  } else {
    elements.deltaPz.style.display = "none";
    elements.deltaPxy.style.display = "none";
  }
}

// --- TELEMETRY & LOGGING ---
let lastLogTime = 0;

function appendTelemetryRow(time) {
  if (!activeResult || !activeResult.valid) return;

  const row = {
    time: time.toFixed(2),
    material: state.materialName,
    mode: state.useCorrections ? "CORRECTED" : "BASELINE",
    Vc: state.Vc,
    t: state.t.toFixed(3),
    w: state.w.toFixed(2),
    gamma0: state.gamma0_deg,
    Pz: activeResult.Pz.toFixed(1),
    Pxy: activeResult.Pxy.toFixed(1),
    Pz_base: baselineResult ? baselineResult.Pz.toFixed(1) : "-",
    Pxy_base: baselineResult ? baselineResult.Pxy.toFixed(1) : "-",
    beta: activeResult.beta_deg.toFixed(1),
    tc: activeResult.t_chip.toFixed(3)
  };

  state.logHistory.unshift(row);
  if (state.logHistory.length > state.maxLogRows) state.logHistory.pop();

  // Strip chart rolling history
  const ch = state.chartHistory;
  ch.time.push(time);
  ch.Pz_corr.push(activeResult.Pz);
  ch.Pxy_corr.push(activeResult.Pxy);
  ch.Pz_base.push(baselineResult ? baselineResult.Pz : activeResult.Pz);
  ch.Pxy_base.push(baselineResult ? baselineResult.Pxy : activeResult.Pxy);

  if (ch.time.length > 120) {
    ch.time.shift();
    ch.Pz_corr.shift();
    ch.Pxy_corr.shift();
    ch.Pz_base.shift();
    ch.Pxy_base.shift();
  }

  updateTelemetryTable();
}

function updateTelemetryTable() {
  const tbody = elements.telemetryTableBody;
  if (!tbody) return;
  tbody.innerHTML = state.logHistory.slice(0, 8).map(r => `
    <tr>
      <td>${r.time}s</td>
      <td><span class="badge-tag ${r.mode === 'CORRECTED' ? 'badge-corr' : 'badge-scope'}">${r.mode}</span></td>
      <td>${r.Vc}</td>
      <td>${r.t}</td>
      <td>${r.Pz} N</td>
      <td>${r.Pxy} N</td>
      <td>${r.Pz_base} N</td>
      <td>${r.Pxy_base} N</td>
      <td>${r.beta}°</td>
      <td>${r.tc}</td>
    </tr>
  `).join("");
}

function exportLogCSV() {
  if (!state.logHistory.length) {
    alert("No logged points yet. Let the digital twin run for a few seconds first.");
    return;
  }
  const headers = ["time_s", "mode", "material", "Vc_m_min", "t_mm", "w_mm", "gamma0_deg",
                   "Pz_N", "Pxy_N", "Pz_baseline_N", "Pxy_baseline_N", "beta_deg", "chip_thk_mm"];
  const csvRows = [headers.join(",")];
  state.logHistory.forEach(r => {
    csvRows.push([r.time, r.mode, r.material, r.Vc, r.t, r.w, r.gamma0,
                  r.Pz, r.Pxy, r.Pz_base, r.Pxy_base, r.beta, r.tc].join(","));
  });

  const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `twin_machining_log_${state.materialName}_${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// --- CANVAS RENDERING ENGINES ---
let animCtx, circleCtx, chartCtx;

function setupCanvases() {
  const handleHiDPI = (canvas) => {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    return { ctx, width: rect.width, height: rect.height };
  };

  animCtx = handleHiDPI(elements.canvasAnim).ctx;
  circleCtx = handleHiDPI(elements.canvasCircle).ctx;
  chartCtx = handleHiDPI(elements.canvasChart).ctx;

  window.addEventListener("resize", () => {
    animCtx = handleHiDPI(elements.canvasAnim).ctx;
    circleCtx = handleHiDPI(elements.canvasCircle).ctx;
    chartCtx = handleHiDPI(elements.canvasChart).ctx;
  });
}

// --- ANIMATED CHIP & TOOL VIEW ---
const tracers = [];
for (let i = 0; i < 90; i++) {
  tracers.push({
    layer: Math.random(), // 0 to 1 across uncut thickness t
    phase: Math.random()  // position along stream
  });
}

function drawMachiningAnimation(ctx, width, height, dt) {
  ctx.clearRect(0, 0, width, height);

  if (!activeResult || !activeResult.valid) {
    ctx.fillStyle = "#ef4444";
    ctx.font = "14px monospace";
    ctx.fillText("Invalid cutting condition", width / 2 - 80, height / 2);
    return;
  }

  const originX = width * 0.48;
  const originY = height * 0.62;
  const t = state.t;
  const g = activeResult.gamma0_rad;
  const b = activeResult.beta_rad;
  const r = activeResult.r;
  const tc = activeResult.t_chip;

  // Visual scaling: scale so uncut thickness t looks substantial
  const scale = (height * 0.28) / Math.max(t, 0.05);
  const t_px = t * scale;
  const tc_px = tc * scale;
  const shearLen = t_px / Math.sin(b);

  // Shear plane endpoint P (relative to tool tip at origin)
  const Px = -t_px / Math.tan(b);
  const Py = -t_px;

  // Direction along rake face
  const ux = Math.sin(g);
  const uy = -Math.cos(g);
  const chipLength = height * 0.65;

  ctx.save();
  ctx.translate(originX, originY);

  // 1. Workpiece block
  ctx.beginPath();
  ctx.moveTo(-width * 0.45, Py);
  ctx.lineTo(Px, Py);
  ctx.lineTo(0, 0); // tool tip
  ctx.lineTo(0, height * 0.32);
  ctx.lineTo(-width * 0.45, height * 0.32);
  ctx.closePath();
  ctx.fillStyle = "#1e293b";
  ctx.strokeStyle = "#475569";
  ctx.lineWidth = 1.5;
  ctx.fill();
  ctx.stroke();

  // 2. Chip block leaving along rake face
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(Px, Py);
  ctx.lineTo(Px + chipLength * ux, Py + chipLength * uy);
  ctx.lineTo(chipLength * ux, chipLength * uy);
  ctx.closePath();

  // Gradient for chip
  const chipGrad = ctx.createLinearGradient(0, 0, chipLength * ux, chipLength * uy);
  chipGrad.addColorStop(0, "#f59e0b");
  chipGrad.addColorStop(1, "#d97706");
  ctx.fillStyle = chipGrad;
  ctx.strokeStyle = "#b45309";
  ctx.lineWidth = 1.5;
  ctx.fill();
  ctx.stroke();

  // 3. Cutting Tool (Wedge)
  const toolH = height * 0.45;
  const toolBackX = toolH * 0.75;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(toolH * ux, toolH * uy);
  ctx.lineTo(toolBackX, toolH * uy);
  ctx.lineTo(toolBackX, height * 0.25);
  ctx.lineTo(0, 0);
  ctx.closePath();

  const toolGrad = ctx.createLinearGradient(0, 0, toolBackX, height * 0.25);
  toolGrad.addColorStop(0, "#334155");
  toolGrad.addColorStop(1, "#0f172a");
  ctx.fillStyle = toolGrad;
  ctx.strokeStyle = "#64748b";
  ctx.lineWidth = 1.8;
  ctx.fill();
  ctx.stroke();

  // 4. Shear plane line
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(Px, Py);
  ctx.setLineDash([4, 4]);
  ctx.strokeStyle = "#ef4444";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.setLineDash([]);

  // 5. Flow Tracers
  const speedScale = 0.85 * (state.Vc / 100);
  tracers.forEach(tr => {
    tr.phase = (tr.phase + dt * speedScale * 0.4) % 1.0;
    const y_loc = -tr.layer * t_px;
    const xs = y_loc / Math.tan(b); // shear plane crossing x coordinate

    const span = width * 0.38;
    const currentX = -span + tr.phase * (span + Px + chipLength * 0.6);

    ctx.fillStyle = "#ffffff";
    if (currentX <= xs) {
      // Moving in uncut workpiece along velocity vector Vc
      ctx.beginPath();
      ctx.arc(currentX, y_loc, 2, 0, Math.PI * 2);
      ctx.fill();
    } else {
      // Flowing up the rake face along chip hodograph
      const distAlongShear = (currentX - xs) * r;
      if (distAlongShear < chipLength) {
        const chipPtX = xs + distAlongShear * ux;
        const chipPtY = y_loc + distAlongShear * uy;
        ctx.beginPath();
        ctx.arc(chipPtX, chipPtY, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  });

  // 6. Velocity & Annotation overlays
  ctx.strokeStyle = "#06b6d4";
  ctx.fillStyle = "#06b6d4";
  ctx.lineWidth = 2.5;

  // Velocity arrow Vc
  drawArrow(ctx, -width * 0.35, Py * 0.4, -width * 0.22, Py * 0.4);
  ctx.font = "11px 'JetBrains Mono', monospace";
  ctx.fillText(`Vc = ${state.Vc} m/min`, -width * 0.34, Py * 0.4 - 8);

  // Velocity arrow Vchip
  const vchipX = chipLength * 0.45 * ux;
  const vchipY = chipLength * 0.45 * uy;
  ctx.strokeStyle = "#f59e0b";
  ctx.fillStyle = "#f59e0b";
  drawArrow(ctx, vchipX, vchipY, vchipX + 35 * ux, vchipY + 35 * uy);
  ctx.fillText(`Vchip = ${(activeResult.V_chip * 60).toFixed(1)} m/min`, vchipX - 70, vchipY - 8);

  // Uncut thickness dimension
  ctx.strokeStyle = "#94a3b8";
  ctx.fillStyle = "#94a3b8";
  ctx.lineWidth = 1;
  const dimX = -width * 0.38;
  ctx.beginPath();
  ctx.moveTo(dimX, 0); ctx.lineTo(dimX, Py);
  ctx.stroke();
  drawArrow(ctx, dimX, -4, dimX, 0);
  drawArrow(ctx, dimX, Py + 4, dimX, Py);
  ctx.fillText(`t = ${t.toFixed(2)} mm`, dimX + 8, Py / 2 + 4);

  // Shear angle beta label
  ctx.fillStyle = "#ef4444";
  ctx.fillText(`β = ${activeResult.beta_deg.toFixed(1)}°`, Px * 0.6 - 15, Py * 0.4);

  ctx.restore();
}

function drawArrow(ctx, fromX, fromY, toX, toY) {
  const headLen = 6;
  const dx = toX - fromX;
  const dy = toY - fromY;
  const angle = Math.atan2(dy, dx);
  ctx.beginPath();
  ctx.moveTo(fromX, fromY);
  ctx.lineTo(toX, toY);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(toX, toY);
  ctx.lineTo(toX - headLen * Math.cos(angle - Math.PI / 6), toY - headLen * Math.sin(angle - Math.PI / 6));
  ctx.lineTo(toX - headLen * Math.cos(angle + Math.PI / 6), toY - headLen * Math.sin(angle + Math.PI / 6));
  ctx.closePath();
  ctx.fill();
}

// --- MERCHANT FORCE CIRCLE ---
function drawMerchantCircle(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);

  if (!activeResult || !activeResult.valid) return;

  const R = activeResult.R;
  const Pz = activeResult.Pz;
  const Pxy = activeResult.Pxy;
  const g = activeResult.gamma0_rad;
  const b = activeResult.beta_rad;

  const centerX = width * 0.32;
  const centerY = height * 0.65;
  const maxForce = Math.max(R, (baselineResult ? baselineResult.R : 0), 100);
  const scale = (Math.min(width, height) * 0.62) / maxForce;

  const endX = centerX + Pz * scale;
  const endY = centerY - Pxy * scale;

  ctx.save();

  // Circle with diameter R
  const circleMidX = (centerX + endX) / 2;
  const circleMidY = (centerY + endY) / 2;
  const circleRad = (R * scale) / 2;

  ctx.beginPath();
  ctx.arc(circleMidX, circleMidY, circleRad, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
  ctx.lineWidth = 1.2;
  ctx.setLineDash([3, 3]);
  ctx.stroke();
  ctx.setLineDash([]);

  // Draw Resultant Vector R
  ctx.strokeStyle = "#f8fafc";
  ctx.fillStyle = "#f8fafc";
  ctx.lineWidth = 2.4;
  drawArrow(ctx, centerX, centerY, endX, endY);
  ctx.font = "bold 11px 'JetBrains Mono', monospace";
  ctx.fillText(`R = ${Math.round(R)} N`, endX + 8, endY - 4);

  // Optional: Baseline comparison vector (dashed)
  if (state.useCorrections && state.showBaseline && baselineResult && baselineResult.valid) {
    const baseEndX = centerX + baselineResult.Pz * scale;
    const baseEndY = centerY - baselineResult.Pxy * scale;
    ctx.strokeStyle = "rgba(148, 163, 184, 0.6)";
    ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    drawArrow(ctx, centerX, centerY, baseEndX, baseEndY);
    ctx.fillText(`R_base = ${Math.round(baselineResult.R)} N`, baseEndX + 8, baseEndY + 12);
    ctx.setLineDash([]);
  }

  // Orthogonal Force Components (Pz and Pxy)
  // Pz (Cutting direction, horizontal)
  ctx.strokeStyle = "#10b981";
  ctx.fillStyle = "#10b981";
  ctx.lineWidth = 1.8;
  drawArrow(ctx, centerX, centerY, endX, centerY);
  ctx.fillText(`Pz: ${Math.round(Pz)} N`, centerX + (endX - centerX) / 2 - 20, centerY + 16);

  // Pxy (Thrust direction, vertical)
  ctx.strokeStyle = "#f43f5e";
  ctx.fillStyle = "#f43f5e";
  drawArrow(ctx, endX, centerY, endX, endY);
  ctx.fillText(`Pxy: ${Math.round(Pxy)} N`, endX + 8, centerY - (centerY - endY) / 2);

  // Rake Face Components: Friction F and Normal N
  // Direction along tool face: (sin g, cos g)
  const projF = activeResult.F * scale;
  const projN = activeResult.N * scale;
  const F_endX = centerX + projF * Math.sin(g);
  const F_endY = centerY - projF * Math.cos(g);

  ctx.strokeStyle = "#a855f7";
  ctx.fillStyle = "#a855f7";
  drawArrow(ctx, centerX, centerY, F_endX, F_endY);
  ctx.fillText(`F: ${Math.round(activeResult.F)} N`, F_endX - 45, F_endY - 6);

  ctx.strokeStyle = "#38bdf8";
  ctx.fillStyle = "#38bdf8";
  drawArrow(ctx, F_endX, F_endY, endX, endY);
  ctx.fillText(`N: ${Math.round(activeResult.N)} N`, (F_endX + endX) / 2 + 6, (F_endY + endY) / 2 - 6);

  // Shear Plane Components: Shear Force Ps and Normal PN
  const Ps_len = activeResult.Ps * scale;
  const Ps_endX = centerX + Ps_len * Math.cos(b);
  const Ps_endY = centerY - Ps_len * Math.sin(b);

  ctx.strokeStyle = "#f59e0b";
  ctx.fillStyle = "#f59e0b";
  drawArrow(ctx, centerX, centerY, Ps_endX, Ps_endY);
  ctx.fillText(`Ps: ${Math.round(activeResult.Ps)} N`, Ps_endX - 35, Ps_endY + 14);

  // Info box
  ctx.fillStyle = "rgba(15, 23, 42, 0.75)";
  ctx.fillRect(8, 8, 220, 52);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
  ctx.strokeRect(8, 8, 220, 52);
  ctx.fillStyle = "#cbd5e1";
  ctx.font = "10px 'JetBrains Mono', monospace";
  ctx.fillText(`μ_eff = ${activeResult.mu_eff.toFixed(2)} (η = ${activeResult.eta_deg.toFixed(1)}°)`, 16, 26);
  ctx.fillText(`γ0 = ${state.gamma0_deg}° | β = ${activeResult.beta_deg.toFixed(1)}°`, 16, 42);

  ctx.restore();
}

// --- LIVE FORCE OSCILLOSCOPE (STRIP CHART) ---
function drawOscilloscope(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);

  const ch = state.chartHistory;
  if (!ch.time.length) return;

  const padLeft = 45;
  const padRight = 15;
  const padTop = 15;
  const padBottom = 25;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  // Grid & axis
  ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 4; i++) {
    const y = padTop + (plotH / 4) * i;
    ctx.moveTo(padLeft, y);
    ctx.lineTo(width - padRight, y);
  }
  ctx.stroke();

  // Y-axis max scale
  const allForces = [...ch.Pz_corr, ...ch.Pxy_corr, ...ch.Pz_base, ...ch.Pxy_base];
  const maxForce = Math.max(...allForces, 100) * 1.25;

  ctx.fillStyle = "#64748b";
  ctx.font = "9px 'JetBrains Mono', monospace";
  ctx.fillText(`${Math.round(maxForce)} N`, 4, padTop + 8);
  ctx.fillText(`${Math.round(maxForce / 2)} N`, 4, padTop + plotH / 2 + 4);
  ctx.fillText(`0 N`, 18, padTop + plotH + 2);

  // Time window: last 12 seconds
  const tMax = ch.time[ch.time.length - 1];
  const tMin = Math.max(0, tMax - 10);

  const getX = t => padLeft + ((t - tMin) / Math.max(tMax - tMin, 0.1)) * plotW;
  const getY = f => padTop + plotH - (f / maxForce) * plotH;

  // Plot helper
  const drawLine = (data, color, isDashed = false) => {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = isDashed ? 1.4 : 2;
    if (isDashed) ctx.setLineDash([4, 4]);
    else ctx.setLineDash([]);

    let started = false;
    for (let i = 0; i < ch.time.length; i++) {
      if (ch.time[i] < tMin) continue;
      const x = getX(ch.time[i]);
      const y = getY(data[i]);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else { ctx.lineTo(x, y); }
    }
    ctx.stroke();
    ctx.setLineDash([]);
  };

  // Plot baseline (if enabled)
  if (state.useCorrections && state.showBaseline) {
    drawLine(ch.Pz_base, "rgba(16, 185, 129, 0.4)", true);
    drawLine(ch.Pxy_base, "rgba(244, 63, 94, 0.4)", true);
  }

  // Plot active
  drawLine(ch.Pz_corr, "#10b981", false);
  drawLine(ch.Pxy_corr, "#f43f5e", false);
}

// --- MAIN ANIMATION LOOP ---
let lastTimestamp = 0;

function animationLoop(timestamp) {
  if (!lastTimestamp) lastTimestamp = timestamp;
  const dt = (timestamp - lastTimestamp) / 1000;
  lastTimestamp = timestamp;

  if (state.isRunning && dt < 0.2) {
    state.simTime += dt * state.simSpeed;

    // Append to telemetry table every 0.15s
    if (state.simTime - lastLogTime >= 0.15) {
      appendTelemetryRow(state.simTime);
      lastLogTime = state.simTime;
    }
  }

  // Draw visualizations
  drawMachiningAnimation(animCtx, elements.canvasAnim.width / (window.devicePixelRatio || 1),
                                  elements.canvasAnim.height / (window.devicePixelRatio || 1), dt);
  drawMerchantCircle(circleCtx, elements.canvasCircle.width / (window.devicePixelRatio || 1),
                                elements.canvasCircle.height / (window.devicePixelRatio || 1));
  drawOscilloscope(chartCtx, elements.canvasChart.width / (window.devicePixelRatio || 1),
                             elements.canvasChart.height / (window.devicePixelRatio || 1));

  requestAnimationFrame(animationLoop);
}

// Initialize on DOM load
window.addEventListener("DOMContentLoaded", initDOM);
