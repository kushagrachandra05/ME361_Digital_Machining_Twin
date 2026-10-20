"""calibrate.py -- fit correction factors on TRAIN data, report on HELD-OUT data.

Expected CSV schema (one row = one steady-state averaged cut):
    source, Vc_m_min, t_mm, w_mm, gamma0_deg, Pz_N, Pxy_N
    source in {lab_oblique, tube_heldout, literature}
For the lab's oblique-cutting runs map: Pz <- Ftc(=Fz), Pxy <- sqrt(Frc^2+Ffc^2) (see notebook 03).
"""
import numpy as np, pandas as pd
from dataclasses import replace
from scipy.optimize import least_squares
from orthocut import Material, Tool, Cut, Corrections, solve

# parameter vector layout -> (name, initial, lower, upper)
PARAMS = {
    "mu":     (0.5, 0.05, 1.5),     # base friction coefficient (Tool.mu)
    "tau_k":  (1.0, 0.5, 1.5),      # multiplier on tabulated tau_s
    "c_rate": (0.0, -0.1, 0.3),     # strain-rate term
    "m_mu":   (0.0, -0.5, 0.5),     # speed dependence of friction
    "Ke_z":   (0.0, 0.0, 60.0),     # N/mm edge force, cutting direction
    "Ke_xy":  (0.0, 0.0, 60.0),     # N/mm edge force, thrust direction
}

def predict(df, mat, free, theta, base_tool=Tool(), shear_model="ernst_merchant"):
    p = {k: v[0] for k, v in PARAMS.items()}; p.update(dict(zip(free, theta)))
    out = []
    for _, r in df.iterrows():
        tool = Tool(r.gamma0_deg, p["mu"])
        m = Material(mat.name, mat.tau_s*p["tau_k"], mat.sigma_y)
        c = Corrections(c_rate=p["c_rate"], m_mu=p["m_mu"], Ke_z=p["Ke_z"], Ke_xy=p["Ke_xy"], shear_model=shear_model)
        try: s = solve(m, tool, Cut(r.Vc_m_min, r.t_mm, r.w_mm), c); out.append((s.Pz, s.Pxy))
        except ValueError: out.append((np.nan, np.nan))
    return np.array(out)

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
                      R2=float(1 - np.nansum(e**2)/np.sum((obs[:, j]-obs[:, j].mean())**2)))
    return out, pr

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
