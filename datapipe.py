"""
datapipe.py -- load external orthogonal-cutting data, put it in ONE canonical schema,
and apply the project's scope rules, logging every dropped row and why.

Canonical schema (forces per the slides: Pz = Fc direction, Pxy = Ff/thrust direction):
  source,test_id,material,vc_m_min,f_mm_rev,t_mm,w_mm,gamma0_deg,Fc_N,Ff_N,rn_um,status,chip_form,bue_flag,note
  * t_mm = uncut chip thickness (= f for tube/orthogonal cutting at 90 deg entering angle)
  * Fc_N, Ff_N are TOTAL forces for width w_mm.  ETH tables are per 1 mm width -> w_mm=1.
"""
import re, io, subprocess
import numpy as np, pandas as pd

COLS = ["source","test_id","material","vc_m_min","f_mm_rev","t_mm","w_mm","gamma0_deg",
        "Fc_N","Ff_N","rn_um","status","chip_form","bue_flag","note"]
# optional provenance columns (filled with defaults if a CSV does not have them)
OPT_COLS = {"sFc_N": np.nan, "sFf_N": np.nan, "h_chip_um": np.nan, "wear": "NA", "digitised": 0}

# ---- ETH (Klippel et al.) table-row parser -------------------------------------------
# Row layout in Tables B.14/B.15:  id vc f Fc sFc Ff sFf rn srn h_avg s_h l_cut T_chip Wear Status
# Status is one of: ok, short, questionable, initially stable, saturation, instable, error (may be 2 words).
_ROW = re.compile(r"^\s*(V\d{4})\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+"
                  r"([\d.]+)\s+([\d.]+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s+([LMH])\s+([A-Za-z]+(?: [A-Za-z]+)?)\s*$")
_ETH_CK45 = range(69, 301)   # paper, App. B: Ti6Al4V = V0001-V0068 & V0301-V0520, Ck45 = V0069-V0300

def _num(s):
    try: return float(s)
    except ValueError: return np.nan

def parse_eth_text(text: str) -> pd.DataFrame:
    """Parse rows copied/extracted from the ETH tables. Lines that start with a test id but do not
    match are returned in df.attrs['unparsed'] so nothing is silently lost (the PDF text layer is messy).
    Lines that are only lists of test ids (the test-plan matrices in Sec. 2) are ignored."""
    rows, bad = [], []
    for line in text.splitlines():
        if not re.match(r"^\s*V\d{4}\s+[\d.]", line): continue      # not a results-table row
        m = _ROW.match(line)
        if not m: bad.append(line); continue
        tid, vc, f, Fc, sFc, Ff, sFf, rn, srn, h, sh, lcut, T, wear, st = m.groups()
        mat = "Ck45" if int(tid[1:]) in _ETH_CK45 else "Ti6Al4V"
        rows.append(dict(source="ETH_TiCk45", test_id=tid, material=mat, vc_m_min=float(vc), f_mm_rev=float(f),
                         t_mm=float(f), w_mm=1.0, gamma0_deg=0.0, Fc_N=float(Fc), Ff_N=float(Ff), rn_um=float(rn),
                         status=st.replace(" ", "_"), chip_form=_eth_chip_form(mat, float(vc)),
                         bue_flag=0, note="parsed from arXiv:2209.04197 App. B (forces per 1 mm width)",
                         sFc_N=float(sFc), sFf_N=float(sFf), h_chip_um=_num(h), wear=wear, digitised=0))
    df = pd.DataFrame(rows, columns=COLS + list(OPT_COLS)); df.attrs["unparsed"] = bad
    return df

def _eth_chip_form(mat, vc):
    """Paper Sec. 3.2: Ti6Al4V segments at ALL conditions; Ck45 starts to segment 'at higher cutting speeds
    and feeds' (Table 10 shows it at 450 m/min). No numeric threshold is given -> label vc>150 as 'onset'."""
    if mat == "Ti6Al4V": return "segmented"
    return "continuous" if vc <= 150 else "segmentation_onset"

def parse_eth_pdf(pdf_path) -> pd.DataFrame:
    """pdftotext -layout on the arXiv PDF, then parse_eth_text."""
    txt = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout
    return parse_eth_text(txt)

def load_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in COLS if c not in df.columns]
    if missing: raise ValueError(f"{path}: missing columns {missing}")
    for c, v in OPT_COLS.items():
        if c not in df.columns: df[c] = v
    return df[COLS + list(OPT_COLS)]

# ---- scope rules --------------------------------------------------------------------
def flag_bue_eth_ck45(df):
    """ETH paper, Sec. 3.2: Ck45 chips show BUE traces up to vc=50 m/min at all feeds, at 150 m/min only
    for f=0.02, none at 450. Conservative rule: BUE-suspect if vc<=100, or vc<=150 and f<=0.02."""
    m = (df.source == "ETH_TiCk45") & (df.material == "Ck45")
    df.loc[m & ((df.vc_m_min <= 100) | ((df.vc_m_min <= 150) & (df.f_mm_rev <= 0.02))), "bue_flag"] = 1
    return df

def apply_scope(df, allow_short=True, short_max_cv=0.05, require_continuous_chip=False, max_rn_um=None,
                drop_wear=("H",), min_vc=None, verbose=True):
    """Return (kept, dropped). Every dropped row carries a 'drop_reason'.
    * status: only 'ok' (and 'short' if allow_short). ETH App. B: 'short' tests are usable only if the force
      std is small -> kept only when sFc/Fc and sFf/Ff <= short_max_cv (if std is available).
    * wear: wear is out of project scope -> heavy-wear tests (class H) dropped.
    * min_vc: optional lower speed bound (e.g. 150 for Ck45 to stay clear of BUE)."""
    df = flag_bue_eth_ck45(df.copy())
    for c, v in OPT_COLS.items():
        if c not in df.columns: df[c] = v
    ok_status = {"ok", "short"} if allow_short else {"ok"}
    reasons = pd.Series("", index=df.index)
    reasons[~df.status.isin(ok_status)] += "status;"
    cv = np.maximum(df.sFc_N/df.Fc_N.where(df.Fc_N > 0), df.sFf_N/df.Ff_N.where(df.Ff_N > 0))
    reasons[(df.status == "short") & (cv > short_max_cv)] += "short_unstable;"
    if drop_wear: reasons[df.wear.isin(drop_wear)] += "wear;"
    if min_vc is not None: reasons[df.vc_m_min < min_vc] += "below_min_vc;"
    reasons[df.bue_flag == 1] += "BUE;"
    reasons[(df.Fc_N <= 0) | (df.Ff_N <= 0)] += "nonpositive_force;"
    if require_continuous_chip: reasons[df.chip_form != "continuous"] += "segmented_chip;"
    if max_rn_um is not None: reasons[df.rn_um > max_rn_um] += "edge_radius;"
    keep = reasons == ""
    kept, dropped = df[keep].copy(), df[~keep].assign(drop_reason=reasons[~keep])
    if verbose:
        print(f"kept {len(kept)} / {len(df)} rows; dropped {len(dropped)}")
        if len(dropped): print(dropped.drop_reason.value_counts().to_string())
    return kept, dropped

def to_twin_units(df):
    """Per-mm force coefficient columns used throughout: Kc = Fc/(w t), Kf = Ff/(w t)  [N/mm^2 = MPa]."""
    d = df.copy(); d["Pz_N"] = d.Fc_N; d["Pxy_N"] = d.Ff_N; d["Vc_m_min"] = d.vc_m_min
    d["Kc_MPa"] = d.Fc_N/(d.w_mm*d.t_mm); d["Kf_MPa"] = d.Ff_N/(d.w_mm*d.t_mm)
    d["mu_app"] = (d.Ff_N + d.Fc_N*np.tan(np.radians(d.gamma0_deg)))/(d.Fc_N - d.Ff_N*np.tan(np.radians(d.gamma0_deg)))
    return d
