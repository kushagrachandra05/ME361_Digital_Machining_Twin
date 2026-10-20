"""
twin_anim.py -- matplotlib prototype of the orthogonal-cutting digital twin.
Left : chip-formation animation (tool fixed, workpiece moves right at Vc).
Right: live Pz / Pxy strip chart + numeric read-out; every frame is logged.
Uncut thickness may vary with time, t(time), as in the sketch's a1(t).
Quasi-static: forces follow the instantaneous t (no dynamics / no thermal / no wear).
"""
from __future__ import annotations
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Polygon, Rectangle
from orthocut import Material, Tool, Cut, Corrections, solve

def run_twin(mat, tool, Vc, t_profile, w=2.0, corr=Corrections(), phi_deg=0.0,
             duration=6.0, fps=20, noise=0.0, seed=0, vis_speed=0.12, out=None):
    """t_profile: float or callable(time_s)->t [mm]. Returns (anim, log DataFrame)."""
    tf = t_profile if callable(t_profile) else (lambda s: t_profile)
    rng = np.random.default_rng(seed)
    times = np.arange(0, duration, 1/fps)
    rows = []
    for s in times:
        ts = float(tf(s)); ramp = 1 - np.exp(-s/0.25)           # engagement transient
        r = solve(mat, tool, Cut(Vc, ts, w), corr, phi_deg)
        n = noise*rng.standard_normal(2)
        rows.append(dict(time_s=s, Vc_m_min=Vc, t_mm=ts, w_mm=w, beta_deg=r.beta_deg,
                         Pz_N=ramp*r.Pz*(1+n[0]), Pxy_N=ramp*r.Pxy*(1+n[1]),
                         Px_N=ramp*r.Px, Py_N=ramp*r.Py, chip_thk_mm=r.t_chip))
    log = pd.DataFrame(rows)

    g = np.radians(tool.gamma0_deg); u = np.array([np.sin(g), np.cos(g)]); nrm = np.array([-np.cos(g), np.sin(g)])
    tmax = float(np.max([tf(s) for s in times])); H = max(tmax*6, 0.6)   # view scale
    fig, (ax, axf) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={'width_ratios': [1.15, 1]})
    ax.set_aspect('equal'); ax.set_xlim(-H*1.6, H*1.0); ax.set_ylim(-H*0.9, H*1.3); ax.axis('off')
    wp = Polygon(np.zeros((5, 2)), fc='#cfd8dc', ec='k'); ax.add_patch(wp)
    ax.text(-H*1.5, -H*0.8, f"{mat.name}  τs={mat.tau_s:.0f} MPa" + (f", σy={mat.sigma_y:.0f} MPa" if mat.sigma_y else ""), fontsize=9)
    tool_poly = Polygon([[0, 0], [H*0.55*np.sin(g), H*0.55*np.cos(g)], [H*0.55*np.sin(g)+H*0.5, H*0.55*np.cos(g)+0.0], [H*0.5, -H*0.35]], fc='#90a4ae', ec='#37474f', zorder=3)
    ax.add_patch(tool_poly)
    chip = Polygon(np.zeros((4, 2)), fc='#ffb74d', ec='#e65100', zorder=2); ax.add_patch(chip)
    shear_line, = ax.plot([], [], 'r--', lw=1.2, zorder=4)
    dots, = ax.plot([], [], 'k.', ms=3, zorder=5)
    top, = ax.plot([], [], 'b-', lw=1.2)
    txt = ax.text(-H*1.55, H*1.15, '', fontsize=10, family='monospace', va='top')
    ax.annotate('', xy=(-H*0.45, -H*0.45), xytext=(-H*1.3, -H*0.45), arrowprops=dict(arrowstyle='->', color='teal', lw=2))
    ax.text(-H*0.9, -H*0.40, f'Vc = {Vc:g} m/min', color='teal', ha='center')

    axf.set_xlim(0, duration); axf.set_ylim(0, max(log.Pz_N.max(), 1)*1.25)
    axf.set_xlabel('time [s]'); axf.set_ylabel('force [N]'); axf.grid(alpha=.3)
    lz, = axf.plot([], [], 'g-', label='Pz (cutting)'); lx, = axf.plot([], [], 'r-', label='Pxy (thrust)')
    axf.legend(loc='upper right'); axf.set_title('Live force feed')
    # tracer particles: (layer height fraction, phase)
    nL, nP = 6, 14
    lay = np.repeat((np.arange(nL)+0.5)/nL, nP); ph0 = np.tile(np.linspace(0, 1, nP, endpoint=False), nL)

    def frame(i):
        s = times[i]; row = log.iloc[i]; ts = row.t_mm; b = np.radians(row.beta_deg)
        tc = row.chip_thk_mm; Vs = vis_speed*H                       # visual speed of workpiece [mm/s]
        r = ts/tc; P = np.array([-ts/np.tan(b), ts]); L = H*1.0
        chip.set_xy([[0, 0], P, P+L*u, L*u])
        shear_line.set_data([0, P[0]], [0, P[1]])
        wp.set_xy([[-H*1.6, -H*0.9], [0, -H*0.9], [0, 0], P, [-H*1.6, ts]])
        top.set_data([-H*1.6, P[0]], [ts, ts])
        # tracers: workpiece layers translate at Vs; after crossing shear plane they move along u at r*Vs
        span = H*1.6; X = []; Y = []
        for yk, p0 in zip(lay, ph0):
            y = yk*ts; xs = -y/np.tan(b)                            # crossing x for this layer
            x = -span + ((p0*span + Vs*s) % (span + H))             # wrapping coordinate
            if x <= xs: X.append(x); Y.append(y)
            else:
                d = (x - xs)*r; q = np.array([xs, y]) + d*u
                if d < L: X.append(q[0]); Y.append(q[1])
        dots.set_data(X, Y)
        lz.set_data(log.time_s[:i+1], log.Pz_N[:i+1]); lx.set_data(log.time_s[:i+1], log.Pxy_N[:i+1])
        txt.set_text(f"t={ts:5.3f} mm  β={row.beta_deg:5.1f}°  chip={tc:5.3f} mm\n"
                     f"Pz ={row.Pz_N:7.1f} N   Pxy={row.Pxy_N:7.1f} N\nPx ={row.Px_N:7.1f} N   Py ={row.Py_N:7.1f} N")
        return chip, shear_line, dots, lz, lx, txt, top
    anim = FuncAnimation(fig, frame, frames=len(times), interval=1000/fps, blit=False)
    if out: log.to_csv(out, index=False)
    return anim, log, fig
