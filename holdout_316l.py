#!/usr/bin/env python3
"""
holdout_316l.py -- held-out check of a preset against literature 316L rows (data/lit_316L.csv).

Nothing here is fitted: it only predicts each row with the preset (baseline = all corrections OFF,
corrected = preset Corrections) and reports errors. Also prints the measured slope/intercept so the
edge-force and friction picture can be compared with the ETH fits.

Usage:  python holdout_316l.py [--preset SS316L] [--csv data/lit_316L.csv]
In a notebook:  from holdout_316l import holdout; display(holdout())
"""
import argparse
import numpy as np, pandas as pd
from orthocut import Cut, Corrections, solve
from twin_anim import load_preset


def holdout(preset: str = "SS316L", csv: str = "data/lit_316L.csv") -> pd.DataFrame:
    lit = pd.read_csv(csv)
    if lit.empty:
        print("no literature rows yet"); return lit
    mat, tool, corr, _ = load_preset(preset)
    out = lit[["source", "test_id", "vc_m_min", "t_mm", "w_mm", "Fc_N", "Ff_N", "digitised"]].copy()
    for lab, c in [("base", Corrections()), ("corr", corr)]:
        r = [solve(mat, tool, Cut(Vc=v, t=t, w=w), corr=c) for v, t, w in zip(lit.vc_m_min, lit.t_mm, lit.w_mm)]
        out[f"Pz_{lab}"] = [x.Pz for x in r]
        out[f"Pxy_{lab}"] = [x.Pxy for x in r]
        out[f"errPz_{lab}_%"] = 100 * (out[f"Pz_{lab}"] - lit.Fc_N) / lit.Fc_N
        out[f"errPxy_{lab}_%"] = 100 * (out[f"Pxy_{lab}"] - lit.Ff_N) / lit.Ff_N
    for lab in ("base", "corr"):
        print(f"{preset} {lab:4s}: MAPE Pz {out[f'errPz_{lab}_%'].abs().mean():5.0f} %   "
              f"Pxy {out[f'errPxy_{lab}_%'].abs().mean():5.0f} %")
    for src, g in lit.groupby("source"):
        if g.t_mm.nunique() >= 2:
            kz, ez = np.polyfit(g.t_mm, g.Fc_N / g.w_mm, 1); kx, ex = np.polyfit(g.t_mm, g.Ff_N / g.w_mm, 1)
            print(f"measured {src}: Pz/w = {kz:.0f} t + {ez:.0f}   Pxy/w = {kx:.0f} t + {ex:.0f}   [N/mm, t in mm]")
    return out.round(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--preset", default="SS316L"); p.add_argument("--csv", default="data/lit_316L.csv")
    a = p.parse_args(); print(holdout(a.preset, a.csv).to_string(index=False))
