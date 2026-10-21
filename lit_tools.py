#!/usr/bin/env python3
"""
lit_tools.py -- semi-automatic entry of literature cutting data into data/lit_316L.csv

Why semi-automatic: publisher sites (ScienceDirect, ResearchGate) refuse scripted downloads, so YOU
fetch the PDF / take a screenshot once; everything after that is automated and every step is verifiable.

Subcommands
  tables   PDF            dump every table pdfplumber can see to CSV + show those that look like force data
  from-table CSV ...      map columns of a dumped table to the canonical schema and append (after validation)
  grid     IMG            write IMG with a labelled pixel grid (read axis-tick pixel positions off it)
  bars     IMG ...        auto-detect bars of one colour, convert to data values, write an overlay for checking
  points   IMG ...        convert pixel coordinates you give (or click, --click) to data values
  append   CSV            validate + append hand-typed rows (same checks as above)
  coverage ETH_CSV        list ETH test ids missing from eth_full.csv (expects 288 Ti6Al4V + 232 Ck45)

Every automated path writes digitised=1 for figure-derived values and refuses rows whose note says FEM/simulation.
"""
import argparse, json, re, sys, subprocess
from pathlib import Path
import numpy as np, pandas as pd

DEFAULT_COLS = ["source","test_id","material","vc_m_min","f_mm_rev","t_mm","w_mm","gamma0_deg",
                "Fc_N","Ff_N","rn_um","status","chip_form","bue_flag","digitised","note"]
FORBIDDEN_NOTE = re.compile(r"\b(?:fem|fea|simulat\w*|predicted|model(?:l)?ed|sph)\b", re.I)

# ------------------------------------------------------------------ validation / append
def target_columns(path: Path):
    if path.exists() and path.stat().st_size > 0:
        return list(pd.read_csv(path, nrows=0).columns)
    return DEFAULT_COLS

def validate(df: pd.DataFrame) -> pd.DataFrame:
    need = ["material","vc_m_min","t_mm","w_mm","Fc_N","Ff_N"]
    miss = [c for c in need if c not in df.columns or df[c].isna().any()]
    if miss: raise SystemExit(f"REFUSED: missing required values in {miss}")
    if "note" in df and df.note.astype(str).str.contains(FORBIDDEN_NOTE).any():
        raise SystemExit("REFUSED: note mentions FEM/simulation -- only experimental data may enter this file")
    bad = df[(df.t_mm <= 0) | (df.t_mm > 1.5) | (df.w_mm <= 0) | (df.Fc_N <= 0) | (df.Ff_N < 0) | (df.vc_m_min <= 0)]
    if len(bad): raise SystemExit(f"REFUSED: implausible rows (check units, N vs N/mm, mm vs um):\n{bad}")
    if (df.Ff_N > 1.5*df.Fc_N).any():
        print("WARNING: Ff > 1.5 Fc in some rows -- check columns are not swapped:\n", df[df.Ff_N > 1.5*df.Fc_N])
    return df

def do_append(rows: pd.DataFrame, out: Path, dry=False):
    cols = target_columns(out)
    defaults = dict(source="LIT", test_id="", status="ok", chip_form="continuous", bue_flag=0, digitised=0,
                    rn_um=np.nan, gamma0_deg=np.nan, f_mm_rev=np.nan, note="")
    for k, v in defaults.items():
        if k not in rows: rows[k] = v
    if rows.f_mm_rev.isna().all(): rows["f_mm_rev"] = rows.t_mm       # tube / orthogonal: f = t
    validate(rows)
    for c in cols:
        if c not in rows: rows[c] = np.nan
    rows = rows[cols]
    print(rows.to_string(index=False))
    if dry: print("\n(dry run: nothing written)"); return
    exists = out.exists() and out.stat().st_size > 0
    rows.to_csv(out, mode="a" if exists else "w", header=not exists, index=False)
    print(f"\nappended {len(rows)} rows -> {out}")

# ------------------------------------------------------------------ PDF tables
def cmd_tables(a):
    import pdfplumber
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True); k = 0; hits = []
    with pdfplumber.open(a.pdf) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            for strat in ({}, {"vertical_strategy": "text", "horizontal_strategy": "text"}):
                tabs = page.extract_tables(strat) if strat else page.extract_tables()
                if tabs: break
            for t in tabs:
                df = pd.DataFrame(t); k += 1; f = outdir/f"p{pn:02d}_t{k:02d}.csv"; df.to_csv(f, index=False, header=False)
                txt = " ".join(df.astype(str).values.ravel()).lower()
                score = sum(w in txt for w in ["fc", "ff", "feed force", "cutting force", "h1", "exp", "n/mm", "[n]"])
                numeric = pd.to_numeric(df.stack(), errors="coerce").notna().mean()
                if score >= 2 and numeric > 0.3: hits.append((f, pn, score, df.shape))
                print(f"page {pn:2d}  table {k:2d}  shape {df.shape}  keyword-score {score}  numeric {numeric:.0%}  -> {f}")
    print("\nLIKELY FORCE TABLES:" if hits else "\nNo obvious force table: try `pdftotext -layout` and read the text, or use `bars`/`points` on a figure.")
    for f, pn, s, sh in hits: print(f"  {f}  (page {pn}, {sh})")
    if a.text:
        subprocess.run(["pdftotext", "-layout", a.pdf, str(outdir/"fulltext.txt")]); print(f"full text -> {outdir/'fulltext.txt'}")

def cmd_from_table(a):
    df = pd.read_csv(a.csv, header=None)
    first = a.skip_rows
    df = df.iloc[first:].reset_index(drop=True)
    colmap = dict(kv.split("=") for kv in a.cols.split(","))                       # t=0,Fc=2,Ff=3
    out = pd.DataFrame({k: pd.to_numeric(df.iloc[:, int(v)].astype(str).str.replace(",", ".").str.extract(r"(-?\d+\.?\d*)")[0], errors="coerce")
                        for k, v in colmap.items()})
    out = out.dropna()
    ren = {"t": "t_mm", "Fc": "Fc_N", "Ff": "Ff_N", "vc": "vc_m_min", "w": "w_mm", "gamma": "gamma0_deg", "rn": "rn_um"}
    out = out.rename(columns=ren)
    for k, c in [("vc", "vc_m_min"), ("w", "w_mm"), ("gamma", "gamma0_deg"), ("rn", "rn_um")]:
        if c not in out and getattr(a, k) is not None: out[c] = getattr(a, k)
    out["material"] = a.material; out["source"] = a.source; out["digitised"] = 0
    out["note"] = a.note or f"{a.source} (table) -- verify against paper"
    out["test_id"] = [f"{a.source}_{i+1:02d}" for i in range(len(out))]
    do_append(out, Path(a.out), a.dry)

# ------------------------------------------------------------------ figures
def _load(img):
    from PIL import Image
    return Image.open(img).convert("RGB")

def cmd_grid(a):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    im = _load(a.img); W, H = im.size
    fig = plt.figure(figsize=(W/100, H/100), dpi=100); ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(im); ax.axis("off")
    for x in range(0, W, a.step): ax.axvline(x, c="r", lw=.4, alpha=.5); ax.text(x+2, 10, str(x), color="r", fontsize=7)
    for y in range(0, H, a.step): ax.axhline(y, c="b", lw=.4, alpha=.5); ax.text(2, y-2, str(y), color="b", fontsize=7)
    fig.savefig(a.out, dpi=100); print(f"grid -> {a.out}: read the y-pixel of two labelled axis ticks and pass --ycal 'pix:value,pix:value'")

def _ycal(s):
    (p1, v1), (p2, v2) = [tuple(map(float, kv.split(":"))) for kv in s.split(",")]
    return lambda py: v1 + (py - p1)*(v2 - v1)/(p2 - p1)

def cmd_bars(a):
    im = np.asarray(_load(a.img)).astype(int); H, W, _ = im.shape
    if a.color: target = np.array([int(x) for x in a.color.split(",")])
    else:                                                   # most common saturated colour
        sat = im.max(2) - im.min(2); m = sat > 60
        q = (im[m]//16*16 + 8); vals, cnt = np.unique(q, axis=0, return_counts=True); target = vals[cnt.argmax()]
        print("auto colour (RGB):", target.tolist())
    mask = (np.abs(im - target).sum(2) < a.tol)
    cols = mask.sum(0) > a.min_height
    runs, start = [], None
    for x, c in enumerate(list(cols) + [False]):
        if c and start is None: start = x
        if not c and start is not None:
            if x - start >= a.min_width: runs.append((start, x - 1))
            start = None
    f = _ycal(a.ycal); res = []
    for (x0, x1) in runs:
        xs = slice(x0 + (x1-x0)//4, x1 - (x1-x0)//4 + 1)          # central half of the bar (avoid edges/error bars)
        top = np.median([np.where(mask[:, x])[0].min() for x in range(xs.start, xs.stop)])
        res.append(dict(x_pix=(x0+x1)/2, top_pix=float(top), value=float(f(top))))
    df = pd.DataFrame(res); print(df.round(3).to_string(index=False))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(W/100, H/100), dpi=100); ax.imshow(im.astype(np.uint8)); ax.axis("off")
    for r in res: ax.plot([r.x_pix-12 if False else r["x_pix"]-14, r["x_pix"]+14], [r["top_pix"]]*2, "k-", lw=1.2); ax.text(r["x_pix"], r["top_pix"]-6, f'{r["value"]:.1f}', ha="center", fontsize=8, color="k")
    fig.savefig(a.overlay, dpi=100, bbox_inches="tight"); print(f"CHECK THE OVERLAY BY EYE -> {a.overlay}")
    df.to_csv(a.out, index=False); print(f"raw values -> {a.out}  (map bars to conditions by hand with `append`, digitised=1)")

def cmd_points(a):
    f = _ycal(a.ycal); xs = _ycal(a.xcal) if a.xcal else (lambda x: x)
    pts = [tuple(map(float, p.split(","))) for p in a.pix.split(";")]
    df = pd.DataFrame([dict(x=xs(px), y=f(py)) for px, py in pts]); print(df.round(4).to_string(index=False)); df.to_csv(a.out, index=False)

def cmd_coverage(a):
    df = pd.read_csv(a.eth); ids = set(df.test_id)
    ti = {f"V{n:04d}" for n in list(range(1, 69)) + list(range(301, 521))}; ck = {f"V{n:04d}" for n in range(69, 301)}
    print(f"rows {len(df)} | Ti expected {len(ti)} found {len(ti & ids)} | Ck45 expected {len(ck)} found {len(ck & ids)}")
    print("missing Ti :", sorted(ti - ids)); print("missing Ck45:", sorted(ck - ids))
    dup = df.test_id[df.test_id.duplicated()].tolist(); print("duplicated ids:", dup)

def cmd_append(a):
    do_append(pd.read_csv(a.rows), Path(a.out), a.dry)

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); s = p.add_subparsers(dest="cmd", required=True)
    t = s.add_parser("tables"); t.add_argument("pdf"); t.add_argument("--outdir", default="data/raw/tables"); t.add_argument("--text", action="store_true"); t.set_defaults(fn=cmd_tables)
    f = s.add_parser("from-table"); f.add_argument("csv"); f.add_argument("--cols", required=True, help="e.g. t=0,Fc=2,Ff=3 (0-based column indices)")
    f.add_argument("--skip-rows", type=int, default=1); f.add_argument("--material", default="AISI316L"); f.add_argument("--source", required=True)
    f.add_argument("--vc", type=float); f.add_argument("--w", type=float, help="width of cut [mm]; use 1 if forces are N/mm"); f.add_argument("--gamma", type=float); f.add_argument("--rn", type=float)
    f.add_argument("--note"); f.add_argument("--out", default="data/lit_316L.csv"); f.add_argument("--dry", action="store_true"); f.set_defaults(fn=cmd_from_table)
    g = s.add_parser("grid"); g.add_argument("img"); g.add_argument("--step", type=int, default=50); g.add_argument("--out", default="grid.png"); g.set_defaults(fn=cmd_grid)
    b = s.add_parser("bars"); b.add_argument("img"); b.add_argument("--ycal", required=True); b.add_argument("--color"); b.add_argument("--tol", type=int, default=90)
    b.add_argument("--min-width", type=int, default=6); b.add_argument("--min-height", type=int, default=5); b.add_argument("--overlay", default="bars_overlay.png"); b.add_argument("--out", default="bars_raw.csv"); b.set_defaults(fn=cmd_bars)
    q = s.add_parser("points"); q.add_argument("img", nargs="?"); q.add_argument("--ycal", required=True); q.add_argument("--xcal"); q.add_argument("--pix", required=True, help="'x,y;x,y;...' pixel coordinates"); q.add_argument("--out", default="points_raw.csv"); q.set_defaults(fn=cmd_points)
    c = s.add_parser("coverage"); c.add_argument("eth"); c.set_defaults(fn=cmd_coverage)
    d = s.add_parser("append"); d.add_argument("rows"); d.add_argument("--out", default="data/lit_316L.csv"); d.add_argument("--dry", action="store_true"); d.set_defaults(fn=cmd_append)
    a = p.parse_args(); a.fn(a)

if __name__ == "__main__": main()