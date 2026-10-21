"""
twin_anim.py -- digital twin animation, STRICTLY within project scope.

Model:   pure orthogonal cutting, single shear plane, steady state (slides, Lecture-2).
Inputs:  Vc, t (constant), tau_s / sigma_y, plus fixed tool constants (gamma0, mu, w).
Not modelled (by design): BUE, thermal effects, wear/flank contact, chip segmentation,
         varying uncut thickness/feed/material properties, start-up/exit transients, vibration.
Because everything is constant within a run, forces are CONSTANT in time; the live panel logs
them every frame (optionally with measurement-style noise, OFF by default) and shows the force circle.

Features added:
- On/off toggle for calibrated corrections (`use_corrections=True/False`).
- Overlay comparison with pure slide baseline (`show_baseline=True`).
- Direct preset loader (`load_preset('SS316L'|'Ck45'|'Ti6Al4V')`).
- Enhanced live log export containing both baseline and corrected predictions.
"""
from __future__ import annotations
import os, sys, json, shutil
# Ensure conda env bin is in PATH so matplotlib finds ffmpeg
env_bin = os.path.dirname(sys.executable)
if env_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = env_bin + ":" + os.environ.get("PATH", "")
if shutil.which("ffmpeg"):
    import matplotlib as mpl
    mpl.rcParams["animation.ffmpeg_path"] = shutil.which("ffmpeg")

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Polygon, Circle
from orthocut import Material, Tool, Cut, Corrections, solve
from calibrate import load_corrections

PRESETS = {
    "SS316L": "data/calib/ss316l_provisional.json",
    "Ck45": "data/calib/ck45_eth.json",
    "Ti6Al4V": "data/calib/ti6al4v_eth.json",
}

def load_preset(name: str):
    """Load one of the calibrated presets by material name or file path.
    Returns (mat, tool, corr, meta)."""
    path = PRESETS.get(name, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Preset file not found: {path}")
    raw_meta = json.load(open(path))
    mat, mu, corr = load_corrections(path)
    tool = Tool(gamma0_deg=raw_meta.get("meta", {}).get("gamma0_deg", 0.0), mu=mu)
    return mat, tool, corr, raw_meta.get("meta", {})

def _arrow(ax, v, color, label, lw=1.8, ls='-'):
    ax.annotate('', xy=v, xytext=(0, 0), arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, ls=ls))
    ax.text(v[0]*1.04, v[1]*1.04, label, color=color, fontsize=8)

def run_twin(mat: Material, tool: Tool, Vc: float, t: float, w: float = 2.0,
             corr: Corrections = Corrections(), use_corrections: bool = True,
             show_baseline: bool = True, phi_deg: float = 0.0,
             duration: float = 6.0, fps: int = 20, noise: float = 0.0,
             seed: int = 0, vis_speed: float = 0.35, out: str | None = None):
    """Returns (anim, log DataFrame, fig).
    t is a single number [mm]: constant by assumption.
    
    Parameters:
      use_corrections: toggle Corrections ON/OFF (OFF = pure lecture-2 slide model).
      show_baseline: if True and use_corrections is True, plots the uncorrected baseline
                     forces alongside corrected forces for direct side-by-side verification.
    """
    active_corr = corr if use_corrections else Corrections()
    res = solve(mat, tool, Cut(Vc, t, w), active_corr, phi_deg)

    # Compute baseline for comparison
    has_comp = use_corrections and show_baseline and (active_corr != Corrections())
    base_res = solve(mat, tool, Cut(Vc, t, w), Corrections(), phi_deg) if has_comp else None

    rng = np.random.default_rng(seed)
    times = np.arange(0, duration, 1/fps)
    n_frames = len(times)

    log_dict = dict(
        time_s=times, Vc_m_min=Vc, t_mm=t, w_mm=w, gamma0_deg=tool.gamma0_deg,
        beta_deg=res.beta_deg,
        Pz_N=res.Pz * (1 + noise*rng.standard_normal(n_frames)),
        Pxy_N=res.Pxy * (1 + noise*rng.standard_normal(n_frames)),
        chip_thk_mm=res.t_chip,
        corrected_mode=int(use_corrections)
    )
    if has_comp and base_res is not None:
        log_dict["Pz_baseline_N"] = base_res.Pz * (1 + noise*rng.standard_normal(n_frames))
        log_dict["Pxy_baseline_N"] = base_res.Pxy * (1 + noise*rng.standard_normal(n_frames))
        log_dict["delta_Pz_pct"] = (res.Pz - base_res.Pz) / base_res.Pz * 100
        log_dict["delta_Pxy_pct"] = (res.Pxy - base_res.Pxy) / base_res.Pxy * 100

    log = pd.DataFrame(log_dict)
    log["Px_N"] = log.Pxy_N * np.sin(np.radians(phi_deg))
    log["Py_N"] = log.Pxy_N * np.cos(np.radians(phi_deg))

    g = np.radians(tool.gamma0_deg); b = np.radians(res.beta_deg); r = res.r; tc = res.t_chip
    u = np.array([np.sin(g), np.cos(g)])                       # rake-face direction (chip flow)
    H = t * 9; L = 0.9 * H                                     # view scale, chip length shown
    fig = plt.figure(figsize=(13.2, 5.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1.2], hspace=0.45)
    ax = fig.add_subplot(gs[:, 0]); axf = fig.add_subplot(gs[0, 1]); axc = fig.add_subplot(gs[1, 1])
    ax.set_aspect('equal'); ax.set_xlim(-H*1.7, H*0.9); ax.set_ylim(-H*0.8, H*1.2); ax.axis('off')
    P = np.array([-t/np.tan(b), t])                            # top end of shear plane (tool tip at origin)

    # workpiece (fixed shape: steady state, constant t)
    ax.add_patch(Polygon([[-H*1.7, -H*0.8], [0, -H*0.8], [0, 0], P, [-H*1.7, t]], fc='#cfd8dc', ec='k', zorder=1))
    # chip: straight rigid parallelogram of constant thickness tc leaving along the rake face
    chip_pts = [[0, 0], list(P), list(P + L*u), list(L*u)]
    ax.add_patch(Polygon(chip_pts, fc='#ffb74d', ec='#e65100', zorder=2))
    # tool: wedge with rake face along u
    tw = H * 0.95
    ax.add_patch(Polygon([[0, 0], list(tw*u), list(tw*u + [tw*0.8, 0]), [tw*0.8, -H*0.3]], fc='#90a4ae', ec='#37474f', zorder=3))
    ax.plot([0, P[0]], [0, P[1]], 'r--', lw=1.3, zorder=4)
    ax.text(P[0]*0.5 - H*0.1, t*1.9, f'shear plane β={res.beta_deg:.1f}°', color='r', fontsize=8, ha='right')
    ax.annotate('', xy=(-H*0.45, -H*0.4), xytext=(-H*1.4, -H*0.4), arrowprops=dict(arrowstyle='->', color='teal', lw=2))
    ax.text(-H*0.9, -H*0.32, f'Vc = {Vc:g} m/min', color='teal', ha='center')
    
    mode_tag = "[CORRECTED MODEL]" if use_corrections else "[PURE SLIDE MODEL]"
    ax.text(-H*1.65, -H*0.72, f"{mat.name}   τs={mat.tau_s:.0f} MPa  {mode_tag}" + (f"\nσy={mat.sigma_y:.0f} MPa" if mat.sigma_y else ""), fontsize=8.5)
    ax.annotate('', xy=(-H*1.55, t), xytext=(-H*1.55, 0), arrowprops=dict(arrowstyle='<->'))
    ax.text(-H*1.5, t*1.35, f'uncut t = {t:g} mm', fontsize=8, va='center')
    tracers, = ax.plot([], [], 'k.', ms=3, zorder=5)
    info = ax.text(-H*1.65, H*1.15, '', fontsize=8.5, family='monospace', va='top')

    nL, nP = 6, 16
    lay = np.repeat((np.arange(nL) + 0.5)/nL, nP)
    ph = np.tile(np.linspace(0, 1, nP, endpoint=False), nL)
    span = H * 1.7

    # ---- force-vs-time panel ----
    max_f = max(res.Pz, (base_res.Pz if base_res else 0), 1)
    axf.set_xlim(0, duration); axf.set_ylim(0, max_f*1.35); axf.grid(alpha=.3)
    axf.set_xlabel('time [s]'); axf.set_ylabel('force [N]')
    title_str = 'Live force feed (steady state)'
    if has_comp: title_str += ' [Solid: Corrected, Dashed: Pure Slide]'
    axf.set_title(title_str, fontsize=9)

    lz, = axf.plot([], [], 'g-', lw=2, label='Pz (cut)')
    lx, = axf.plot([], [], 'r-', lw=2, label='Pxy (thrust)')
    artists = [tracers, lz, lx, info]

    if has_comp and base_res is not None:
        lbz, = axf.plot([], [], 'g--', lw=1.2, alpha=0.7, label='Pz (base)')
        lbx, = axf.plot([], [], 'r--', lw=1.2, alpha=0.7, label='Pxy (base)')
        artists.extend([lbz, lbx])
    axf.legend(loc='center right', fontsize=7.5, framealpha=0.85)

    # ---- Merchant (force) circle panel ----
    Rv = np.array([res.Pz, res.Pxy]); Rm = res.R
    axc.set_aspect('equal')
    axc.set_title('Merchant Force Circle' + ('; γ0=0 ⇒ F≡Pxy, N≡Pz' if abs(tool.gamma0_deg)<1e-9 else ''), fontsize=9)
    axc.axis('off')
    axc.add_patch(Circle(Rv/2, Rm/2, fc='none', ec='0.5', lw=1))
    def leg(unit, color, name):
        unit = np.asarray(unit); p = (Rv @ unit)*unit
        axc.annotate('', xy=p, xytext=(0, 0), arrowprops=dict(arrowstyle='-|>', color=color, lw=1.5))
        axc.plot([p[0], Rv[0]], [p[1], Rv[1]], ':', color=color, lw=1); axc.text(p[0], p[1], name, color=color, fontsize=8)
    axc.annotate('', xy=Rv, xytext=(0, 0), arrowprops=dict(arrowstyle='-|>', color='k', lw=2.2))
    axc.text(Rv[0], Rv[1], ' R', fontsize=9)
    leg((1, 0), 'g', 'Pz'); leg((0, 1), 'r', 'Pxy')
    leg((np.cos(g), -np.sin(g)), 'tab:blue', 'N'); leg((np.sin(g), np.cos(g)), 'tab:purple', 'F')
    leg((np.cos(b), -np.sin(b)), 'tab:orange', 'Ps'); leg((np.sin(b), np.cos(b)), 'tab:brown', 'PN')
    axc.set_xlim(-Rm*0.15, Rm*1.15); axc.set_ylim(-Rm*0.4, Rm*0.75)
    axc.text(0, -Rm*0.38, f"μ_eff={res.mu_eff:.2f}  η={res.eta_deg:.1f}°  β={res.beta_deg:.1f}°  r={res.r:.2f}", fontsize=8)

    def frame(i):
        s = times[i]; Vs = vis_speed * H
        X, Y = [], []
        for yk, p0 in zip(lay, ph):
            y = yk * t; xs = -y / np.tan(b)
            x = -span + ((p0*span + Vs*s) % (span + H*0.2))
            if x <= xs: X.append(x); Y.append(y)
            else:
                d = (x - xs) * r; q = np.array([xs, y]) + d * u
                if d < L: X.append(q[0]); Y.append(q[1])
        tracers.set_data(X, Y)
        lz.set_data(log.time_s[:i+1], log.Pz_N[:i+1])
        lx.set_data(log.time_s[:i+1], log.Pxy_N[:i+1])
        if has_comp and base_res is not None:
            lbz.set_data(log.time_s[:i+1], log.Pz_baseline_N[:i+1])
            lbx.set_data(log.time_s[:i+1], log.Pxy_baseline_N[:i+1])

        row = log.iloc[i]
        txt = (f"chip thickness tc = {tc:5.3f} mm   Vchip = {res.V_chip*60:6.1f} m/min\n"
               f"Pz  = {row.Pz_N:7.1f} N     Pxy = {row.Pxy_N:7.1f} N\n")
        if has_comp and base_res is not None:
            txt += (f"Base Pz  = {base_res.Pz:5.1f} N  Base Pxy = {base_res.Pxy:5.1f} N\n"
                    f"ΔPz = {log.delta_Pz_pct.iloc[0]:+5.1f}%     ΔPxy = {log.delta_Pxy_pct.iloc[0]:+5.1f}%\n")
        info.set_text(txt)
        return artists

    anim = FuncAnimation(fig, frame, frames=len(times), interval=1000/fps, blit=False)
    if out: log.to_csv(out, index=False)
    return anim, log, fig
