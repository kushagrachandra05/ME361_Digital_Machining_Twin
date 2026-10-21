"""calibrate.py -- fit correction factors on TRAIN data, report on HELD-OUT data.

Expected CSV schema (one row = one steady-state averaged cut):
    source, Vc_m_min, t_mm, w_mm, gamma0_deg, Pz_N, Pxy_N
    source in {lab_oblique, tube_heldout, literature}
For the lab's oblique-cutting runs map: Pz <- Ftc(=Fz), Pxy <- sqrt(Frc^2+Ffc^2) (see notebook 03).
"""
import json
import numpy as np, pandas as pd
from dataclasses import replace, asdict
from scipy.optimize import least_squares
from orthocut import Material, Tool, Cut, Corrections, solve, forces_vec

# parameter vector layout -> (name, initial, lower, upper)
PARAMS = {
    "mu":     (0.5, 0.05, 1.5),     # base friction coefficient (Tool.mu)
    "tau_k":  (1.0, 0.3, 6.0),      # multiplier on tabulated tau_s. Upper bound 6 (was 1.5): tau_s = sigma_y/sqrt3
                                    # is INITIAL yield; the shear plane works at strain ~2, so strongly
                                    # work-hardening steels need tau_k ~2.7 (Ck45) to ~5 (316L) (see tau_s_flow_JC).
    "c_rate": (0.0, -0.3, 0.3),     # strain-rate / speed term (lumped, empirical; may go negative = softening)
    "m_mu":   (0.0, -0.5, 0.5),     # speed dependence of friction
    "n_mu":   (0.0, -0.2, 0.8),     # thickness dependence of friction (mu*(t/0.1)^-n_mu)
    "Ke_z":   (0.0, 0.0, 150.0),     # N/mm edge force, cutting direction
    "Ke_xy":  (0.0, 0.0, 150.0),     # N/mm edge force, thrust direction
}

def _corr(p, shear_model):
    return Corrections(c_rate=p["c_rate"], m_mu=p["m_mu"], n_mu=p["n_mu"], Ke_z=p["Ke_z"], Ke_xy=p["Ke_xy"],
                       shear_model=shear_model)

def predict(df, mat, free, theta, base_tool=Tool(), shear_model="ernst_merchant"):
    p = {k: v[0] for k, v in PARAMS.items()}; p.update(dict(zip(free, theta)))
    Pz, Pxy = forces_vec(mat.tau_s*p["tau_k"], df.gamma0_deg.to_numpy(float), p["mu"],
                         df.Vc_m_min.to_numpy(float), df.t_mm.to_numpy(float), df.w_mm.to_numpy(float),
                         _corr(p, shear_model))
    return np.column_stack([Pz, Pxy])

def fit(df_train, mat, free=("mu", "tau_k"), shear_model="ernst_merchant"):
    free = list(free)
    x0 = [PARAMS[k][0] for k in free]; lo = [PARAMS[k][1] for k in free]; hi = [PARAMS[k][2] for k in free]
    obs = df_train[["Pz_N", "Pxy_N"]].to_numpy()
    def res(th):
        pr = predict(df_train, mat, free, th, shear_model=shear_model)
        return np.nan_to_num(((pr - obs)/np.maximum(obs.mean(0), 1e-9)).ravel(), nan=10.0)
    sol = least_squares(res, x0, bounds=(lo, hi))
    return dict(zip(free, sol.x)), sol

def metrics(df, mat, params, shear_model="ernst_merchant"):
    free = list(params); pr = predict(df, mat, free, [params[k] for k in free], shear_model=shear_model)
    obs = df[["Pz_N", "Pxy_N"]].to_numpy(); out = {}
    for j, n in enumerate(["Pz", "Pxy"]):
        e = pr[:, j] - obs[:, j]
        out[n] = dict(RMSE=float(np.sqrt(np.nanmean(e**2))), MAPE_pct=float(np.nanmean(np.abs(e/obs[:, j]))*100),
                      R2=(float(1 - np.nansum(e**2)/np.sum((obs[:, j]-obs[:, j].mean())**2)) if len(obs) > 2 and np.ptp(obs[:, j]) > 0 else float('nan')))
    return out, pr

def bootstrap(df, mat, free, n=200, seed=0, shear_model="ernst_merchant"):
    """Row-resampling bootstrap of the fitted parameters -> DataFrame (n x len(free)).
    Reports the confounding between mu, tau_k and Ke honestly (use percentiles, not just the point fit)."""
    rng = np.random.default_rng(seed); out = []
    for _ in range(n):
        b = df.iloc[rng.integers(0, len(df), len(df))]
        out.append(fit(b, mat, free, shear_model)[0])
    return pd.DataFrame(out)

def leave_one_group_out(df, mat, free, group="Vc_m_min", min_train=8, shear_model="ernst_merchant"):
    """Hold out each value of `group` in turn; returns mean held-out MAPE for Pz and Pxy.
    free=None -> baseline slide model with mu=0.5, tau_k=1 (no fitting)."""
    e = []
    for v in sorted(df[group].unique()):
        tr, te = df[df[group] != v], df[df[group] == v]
        if len(te) == 0 or len(tr) < min_train: continue
        p = {"mu": 0.5} if free is None else fit(tr, mat, free, shear_model)[0]
        m, _ = metrics(te, mat, p, shear_model)
        e.append((m["Pz"]["MAPE_pct"], m["Pxy"]["MAPE_pct"], len(te)))
    e = np.array(e)
    w = e[:, 2]   # weight folds by number of test rows
    return float(np.average(e[:, 0], weights=w)), float(np.average(e[:, 1], weights=w))

def export_corrections(path, mat, params, meta=None, shear_model="ernst_merchant"):
    """Write a JSON the twin (Python or web) can load as the 'corrected' preset."""
    p = {k: v[0] for k, v in PARAMS.items()}; p.update({k: float(v) for k, v in params.items()})
    d = dict(material=mat.name, tau_s_MPa=float(mat.tau_s), sigma_y_MPa=(None if mat.sigma_y is None else float(mat.sigma_y)),
             mu=p["mu"], tau_k=p["tau_k"], corrections=asdict(_corr(p, shear_model)), meta=meta or {})
    with open(path, "w") as f: json.dump(d, f, indent=2)
    return d

def load_corrections(path):
    """-> (Material with tau_s already multiplied by tau_k, mu, Corrections)."""
    d = json.load(open(path))
    return Material(d["material"], d["tau_s_MPa"]*d["tau_k"], d["sigma_y_MPa"]), d["mu"], Corrections(**d["corrections"])

def synthetic_demo(seed=1):
    """FAKE data generated from a 'hidden truth' model -- ONLY to test the pipeline."""
    rng = np.random.default_rng(seed); rows = []
    truth = Corrections(c_rate=0.04, Ke_z=18.0, Ke_xy=12.0)
    for src, Vs in [("lab_oblique", [60, 120, 180, 240]), ("tube_heldout", [90, 150, 210])]:
        for V in Vs:
            for t in [0.05, 0.075, 0.10, 0.125]:
                s = solve(Material("Al7050", 303), Tool(13, 0.62), Cut(V, t, 2.0), truth)
                rows.append(dict(source=src, Vc_m_min=V, t_mm=t, w_mm=2.0, gamma0_deg=13.0,
                                 Pz_N=s.Pz*(1+0.03*rng.standard_normal()), Pxy_N=s.Pxy*(1+0.05*rng.standard_normal())))
    return pd.DataFrame(rows)
