# Entering 316L literature data → `data/lit_316L.csv`

I couldn't pull these automatically: ScienceDirect sits behind a Cloudflare challenge, and the in-IDE browser wasn't working. Open the papers in your own browser and type the numbers in.

## Leads (in priority order)
| id | Paper | Access | What to take |
|---|---|---|---|
| AGMELL2017 | Agmell, Johansson, Laakso, Ahadi, Ståhl, *The influence the uncut chip thickness has on the stagnation point in orthogonal cutting*, Procedia CIRP 58 (2017) 13–18, doi:10.1016/j.procir.2017.03.183 | **Open access (CC BY-NC-ND)**: https://www.sciencedirect.com/science/article/pii/S2212827117303657 | Exp. Fc, Ff vs h1 at vc = 125 m/min (FEM-vs-exp table). Also rake angle, edge radius, width of cut. |
| OUTEIRO_316L | Umbrello, M'Saoubi, Outeiro, IJMTM 47 (2007) 462 (+ Outeiro et al. CIRP Annals 2006 on 316L residual stress) | paywalled | Fc, Ft at vc 100–200 m/min, t 0.1–0.2 mm. Usually shown as bar charts, so digitise. |

## Rules
* One row per steady-state averaged cut. `t_mm` = uncut chip thickness (h1). `w_mm` = width of cut.
  * If the paper gives **N/mm**, set `w_mm = 1`.
  * If it gives total N, use the real width.
* `Fc_N` = cutting-direction force (→ Pz). `Ff_N` = thrust/feed force (→ Pxy).
* `gamma0_deg` = rake angle as stated in the paper, and `rn_um` = edge radius (`NaN` if not given).
* `status` = `ok` unless the paper flags the test.
* `chip_form`: use `continuous` for 316L unless the paper says otherwise.
* `bue_flag` = 1 if the paper mentions BUE at that condition.
* **`digitised` = 1** if you read the value off a plot (WebPlotDigitizer). Otherwise 0, i.e. it came from a table.
* `note`: give the table or figure number, e.g. `Agmell2017 Table 5, experimental`.
* **Never enter FEM/simulated values as data.** Experimental values only.

## After entering
Re-run `04_external_data_validation.ipynb`. Section 6 picks up `lit_316L.csv` automatically. If it has rows, the notebook tests the provisional 316L preset against them, which counts as a held-out check because none of those numbers were used for fitting.
