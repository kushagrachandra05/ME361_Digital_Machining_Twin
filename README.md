# ME361 Digital Machining Twin

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Scope: Lecture 2 Pure Orthogonal](https://img.shields.io/badge/Scope-Lecture%202%20Orthogonal-emerald.svg)](orthocut.py)
[![Interactive Web Twin](https://img.shields.io/badge/Web%20Twin-HTML5%20Canvas%20%2B%20JS-purple.svg)](web/)
[![Report: PDF Available](https://img.shields.io/badge/Report-PDF%20Compiled-red.svg)](ME361_Digital_Machining_Twin_Report.pdf)

A complete **Digital Machining Twin** developed for **ME361 (Manufacturing Processes)**, implementing the **pure orthogonal single-shear-plane model (Lecture 2)** alongside an empirical calibration pipeline, external experimental data validation (ETH Zürich & Lund databases), and a real-time browser-based interactive dashboard.

---

## 📌 Executive Scope & Design Principles

The project strictly adheres to the locked theoretical scope defined in the course lectures:

* **In-Scope Physics:** Pure orthogonal cutting, single shear plane, steady-state cutting.
* **Core Primary Inputs:**
  1. Cutting velocity $V_c$ (m/min)
  2. Uncut chip thickness $t$ / feed (mm)
  3. Workpiece shear/yield strength $\tau_s$ or $\sigma_y$ (MPa, with von Mises fallback $\tau_s = \sigma_y / \sqrt{3}$)
* **Tool Constants & Baseline Assumptions:** Rake angle $\gamma_0$, friction coefficient $\mu$, cutting width $w$ (tube wall thickness).
* **Primary Outputs:** Cutting force $P_z$, thrust force $P_{xy}$ ($P_x$ or $P_y = P_{xy}$, transverse force = 0), resultant force $R$, shear plane angle $\beta$, chip thickness $t_c$, specific cutting pressure $k_c$, real-time animated cutting zone, and live streaming telemetry with CSV export.
* **Strict Exclusions (Non-Extensions):** Built-Up Edge (BUE), thermal softening fields, tool flank wear contact, chip segmentation/serration, and within-run transients. All parameters are constant within each machining run.

---

## 🏗️ Project Architecture

```
ME361_Digital_Machining_Twin/
├── 01_physics_core.ipynb              # Baseline single-shear-plane validation
├── 02_animation_prototype.ipynb        # Kinematic cutting zone & hodograph animation
├── 03_validation_calibration.ipynb     # Synthetic parameter fitting & sensitivity analysis
├── 04_external_data_validation.ipynb   # Full external data validation (ETH & Lund 316L)
├── ME361_Digital_Machining_Twin_Report.pdf # Executive technical report (PDF)
├── generate_report_pdf.py             # Script to build publication-grade PDF report
├── orthocut.py                         # Core analytical physics engine (Lecture 2)
├── twin_anim.py                        # Python animation & live logging engine
├── datapipe.py                         # Canonical schema, unit conversions, scope filters
├── calibrate.py                        # Least-squares & bootstrap calibration engine
├── lit_tools.py                        # Semi-automated literature data extraction CLI
├── holdout_316l.py                     # Held-out benchmark evaluation script
├── data/
│   ├── datasets_catalog.csv            # Registry of 7 candidate machining datasets
│   ├── eth_full.csv                    # 519 parsed orthogonal tube cuts (ETH Zürich)
│   ├── eth_sample.csv                  # 22-row regression test fixture
│   ├── lit_316L.csv                    # 316L experimental cuts (Agmell et al. 2017)
│   └── calib/
│       ├── ck45_eth.json               # Calibrated preset for Ck45 carbon steel
│       ├── ti6al4v_eth.json            # Calibrated preset for Ti6Al4V alloy
│       └── ss316l_provisional.json     # Analytical transfer preset for SS316L
└── web/                                # Standalone browser-based Digital Twin
    ├── index.html                      # Dashboard layout, sliders, canvases, telemetry
    ├── style.css                       # Modern dark glassmorphic styling
    └── twin.js                         # Kinematics, Merchant circle, oscilloscope, CSV
```

---

## 📐 Mathematical Formulation (Lecture 2)

The physics engine (`orthocut.py`) maps the closed-form single shear plane equations:

$$\beta = \frac{\pi}{4} + \frac{\gamma_0}{2} - \frac{\eta}{2} \quad \text{where } \eta = \arctan(\mu) \quad (\text{Ernst-Merchant})$$

$$A_s = \frac{w \cdot t}{\sin \beta}, \qquad P_s = \tau_s \cdot A_s = \frac{\tau_s \cdot w \cdot t}{\sin \beta}$$

$$R = \frac{P_s}{\cos(\beta + \eta - \gamma_0)}$$

$$P_z = R \cos(\eta - \gamma_0), \qquad P_{xy} = R \sin(\eta - \gamma_0)$$

$$\text{Chip Compression Ratio } r = \frac{t}{t_c} = \frac{\sin \beta}{\cos(\beta - \gamma_0)}$$

$$V_{\text{chip}} = r \cdot V_c, \qquad V_s = \frac{V_c \cos \gamma_0}{\cos(\beta - \gamma_0)}$$

---

## 📊 External Experimental Datasets

### 1. ETH Zürich IWF Database (Klippel et al., arXiv:2209.04197 / IJAMT 2024)
* **519 high-precision dry orthogonal tube cuts** on a CNC lathe for Ck45 (AISI 1045) and Ti6Al4V.
* Parameters: $v_c = 10 - 500\text{ m/min}$, $f = 0.01 - 0.40\text{ mm/rev}$, edge hone $r_n \approx 38\ \mu\text{m}$, rake $\gamma_0 = 0^\circ$.
* **Scope Filtering:** Cuts below $150\text{ m/min}$ in Ck45 were dropped due to severe Built-Up Edge (BUE) formation, leaving 95 high-speed, continuous-chip cuts for calibration.

### 2. Lund University 316L Dataset (Agmell et al., Procedia CIRP 58 (2017) 13–18)
* Experimental force measurements for AISI 316L stainless steel at $v_c = 125\text{ m/min}$ across uncut thicknesses $t = 0.10, 0.20, 0.30\text{ mm}$ with $r_n \approx 45\ \mu\text{m}$.
* Extracted semi-automatically into `data/lit_316L.csv` using `lit_tools.py`.

---

## ⚙️ Calibration Engine & Empirical Insights

Fitting the baseline slide equations against real data revealed three key physical phenomena:

1. **Non-Zero Force Intercepts (Edge Ploughing):** The pure slide model predicts $P \to 0$ as $t \to 0$. Real inserts have edge radius ($r_n \approx 38\ \mu\text{m}$), producing positive intercepts ($P_z \approx 13 - 15\text{ N/mm}$, $P_{xy} \approx 100\text{ N/mm}$). Adding calibrated edge terms $K_{e,z}, K_{e,xy}$ eliminates this error.
2. **Friction Scale Effect:** Apparent friction $\mu = F/N$ falls from ~1.85 at $t = 0.01\text{ mm}$ to ~0.50 at $t = 0.20\text{ mm}$. A power-law sensitivity term $n_\mu$ captures this scale effect: $\mu(t) = \mu_{\text{ref}} (t / t_{\text{ref}})^{-n_\mu}$.
3. **Plastic Shear Strain Hardening ($\tau_k$ Multiplier):** Shear strain $\gamma \approx 2 - 3$ along the shear plane work-hardens steels significantly above initial yield. The fitted multiplier $\tau_k = 2.66$ (Ck45) aligns directly with Johnson-Cook flow stress at true shear strain.

### Calibration Summary Table

| Material | In-Scope Cuts | Initial $\tau_s$ | Fitted $\mu$ | Hardening $\tau_k$ | Edge $K_{e,z}$ | Size $n_\mu$ | Baseline MAPE ($P_z / P_{xy}$) | Calibrated MAPE ($P_z / P_{xy}$) |
|---|---|---|---|---|---|---|---|---|
| **Ck45** | 95 ($v_c \ge 150$) | 242.5 MPa | 0.877 | 2.663 | 13.2 N/mm | 0.266 | 28.4% / 37.1% | **6.8% / 8.2%** |
| **Ti6Al4V** | 273 (All speeds) | 501.7 MPa | 0.766 | 0.888 | 15.3 N/mm | 0.419 | 17.2% / 41.5% | **7.1% / 7.8%** |
| **SS316L** | Analytical Preset | 176.1 MPa | 0.877 | 5.439 (JC) | 13.2 N/mm | 0.266 | Theoretical Ref | **Held-Out Benchmark** |

---

## 🎯 Held-Out Validation & Option B Engineering Decision

Evaluating the provisional SS316L preset against the Agmell 2017 literature data:
* **Baseline Slide Model:** MAPE $P_z = 134\%$, MAPE $P_{xy} = 430\%$
* **Calibrated Provisional Model:** MAPE $P_z = 115\%$, MAPE $P_{xy} = 291\%$

### Why Option B?
The provisional model over-predicts because Agmell's tests used commercial CNMG120408 inserts (longitudinal tube turning with $\kappa_r = 95^\circ$ and positive chip-breaker rake), whereas the provisional model assumed $\gamma_0 = 0^\circ$ and transferred friction from Ck45. 

Under **Option B**, we strictly refuse to over-fit or force-tune parameters on three quasi-orthogonal literature points with unmeasured insert geometry. Instead:
* We maintain our **pure theoretical / analytical model** as a clean, transparent baseline.
* The instructor's forthcoming SS316L lab tube data will serve as the **definitive one-shot blind held-out validation test**.

---

## 🌐 Interactive Web Digital Twin (`web/`)

The repository includes a modern, zero-dependency browser-based Digital Twin:

* **Kinematic Cutting Zone:** Real-time animated canvas illustrating workpiece feed, shear plane angle $\beta$, chip curl, and dynamic velocity hodograph ($V_c, V_{\text{chip}}, V_s$).
* **Live Merchant Force Circle:** Vector decomposition showing resultant $R$, components $P_z, P_{xy}$, friction/normal forces $F, N$, and shear/normal forces $P_s, P_N$.
* **Real-Time Oscilloscope:** Live strip chart tracking cutting and thrust forces.
* **Streaming Telemetry Table:** Live tabulated frames with instantaneous CSV export.
* **Dual Model Toggle:** Compare the Calibrated Model against the Pure Slide Baseline with a single click.
* **Assumption Justification Modal:** Interactive reference table explaining physical causes and handling for all 7 slide assumptions.

### Launching the Web Twin

```bash
# Serve the web directory locally
python3 -m http.server 8080 --directory web
```
Then navigate to `http://localhost:8080` in your browser.

---

## 🚀 Quickstart & CLI Usage

### Environment Setup

```bash
git clone git@github.com:kushagrachandra05/ME361_Digital_Machining_Twin.git
cd ME361_Digital_Machining_Twin

# Using conda/pip
pip install numpy pandas matplotlib reportlab pdfplumber
```

### 1. Solve Analytical Orthogonal Cut
```python
from orthocut import Material, Tool, Cut, solve

mat = Material(name="SS316L", tau_s=176.1, sigma_y=305.0)
tool = Tool(gamma0_deg=0.0, mu=0.5)
cut = Cut(Vc=125.0, t=0.10, w=2.0)

res = solve(mat, tool, cut)
print(f"Pz: {res.Pz:.1f} N, Pxy: {res.Pxy:.1f} N, Beta: {res.beta_deg:.1f}°")
```

### 2. Run Python Twin Animation & Export Video
```bash
python twin_anim.py
# Generates twin_demo.mp4 and logs twin_log.csv
```

### 3. Run Held-Out Literature Benchmark
```bash
python holdout_316l.py --preset SS316L
```

### 4. Re-compile Project Technical Report (PDF)
```bash
python generate_report_pdf.py
# Compiles ME361_Digital_Machining_Twin_Report.pdf
```

---

## 📋 Assumption-by-Assumption Justification Matrix

| Lecture 2 Slide Assumption | Physical Reality in External Data | Digital Twin Handling | Scope Status |
|---|---|---|---|
| **1. Perfectly sharp tool ($r_n = 0$)** | Real inserts have hone ($r_n \approx 38\ \mu\text{m}$), causing non-zero force intercept at $t \to 0$. | Calibrated edge terms $K_{e,z}, K_{e,xy}$ added to forces. | **CORRECTED** |
| **2. Constant friction $\mu$** | Apparent $\mu = F/N$ drops from 1.85 to 0.50 as $t$ increases from 0.01 to 0.20 mm. | Thickness sensitivity $n_\mu$ ($\mu \propto t^{-n_\mu}$) models size effect. | **CORRECTED** |
| **3. Shear strength $\tau_s = \sigma_y/\sqrt{3}$** | Shear strain $\gamma \approx 2 - 3$ causes severe work-hardening. | Flow stress multiplier $\tau_k$ calibrated to true shear strain. | **CORRECTED** |
| **4. Continuous chip formation** | Ti6Al4V segments at all conditions; Ck45 is continuous above 150 m/min. | Ck45 used as steel baseline; Ti6Al4V documented as violation. | **IN-SCOPE** |
| **5. No Built-Up Edge (BUE)** | Ck45 chips exhibit severe BUE below 150 m/min. | BUE-suspect rows dropped by `datapipe.apply_scope` with logged reasons. | **FILTERED OUT** |
| **6. Isothermal cutting** | Thermal softening lowers force slightly at high $V_c$. | Speed factor $c_{\text{rate}}$ kept OFF by default to preserve slide scope. | **LOCKED SCOPE** |
| **7. Steady state within a run** | Forces plateau after ~1–2 ms initial contact. | Steady state enforced; live feed demonstrates constant forces. | **LOCKED SCOPE** |

---

## 👥 Authors & Acknowledgments

Group G23
* **Amrit Dwivedi** (240111)
* **Kushagra Chandra** (240585)
* **Course:** Secondary Manufacturing Processes (ME361)
* **Instructor:** Prof. Sarvesh Mishra
* **Data Sources:** ETH Zürich IWF (Klippel et al., 2024); Lund University (Agmell et al., 2017).
