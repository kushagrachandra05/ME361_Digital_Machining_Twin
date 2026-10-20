"""
orthocut.py -- core physics of the ME361 digital machining twin.

Scope (deliberately minimal): PURE ORTHOGONAL CUTTING, single-shear-plane model.
No temperature, no flank wear, no chip-tool interface physics beyond a mean
friction coefficient mu (F/N = mu = tan(eta)).

Notation follows the ME361 lecture slides (Lecture 2):
    Vc    cutting velocity            t     uncut chip thickness
    w     width of cut                gamma0 orthogonal rake angle
    beta  shear angle                 eta   friction angle, mu = tan(eta)
    tau_s shear strength              sigma_y yield strength
    Ps    shear force on shear plane  PN    normal force on shear plane
    F, N  friction / normal force on rake face
    R     resultant force             Pz    force along cutting velocity
    Pxy   thrust force (perpendicular to Pz)   phi: orientation used to split Pxy
    Px = Pxy sin(phi), Py = Pxy cos(phi)   (orthogonal system of first kind)

Units: SI inside the maths. Public inputs: Vc [m/min], t, w [mm], stresses [MPa].
"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
import numpy as np

# ----------------------------------------------------------------- inputs
@dataclass(frozen=True)
class Material:
    name: str
    tau_s: float            # shear strength [MPa]
    sigma_y: float | None = None   # yield strength [MPa]

    @staticmethod
    def tau_from_sigma_y(sigma_y, criterion="mises"):
        """Fallback when tau_s is unknown: Mises sigma_y/sqrt3, Tresca sigma_y/2."""
        return sigma_y / (np.sqrt(3.0) if criterion == "mises" else 2.0)

@dataclass(frozen=True)
class Tool:
    gamma0_deg: float = 13.0   # rake angle (PLACEHOLDER = lab-sheet value; confirm)
    mu: float = 0.5            # mean friction coeff on rake face (calibration knob)

@dataclass(frozen=True)
class Cut:
    Vc: float                  # [m/min]
    t: float                   # uncut chip thickness [mm]
    w: float = 2.0             # width of cut = tube wall thickness [mm]

# ------------------------------------------------- correction factors (all OFF)
@dataclass(frozen=True)
class Corrections:
    """Every factor defaults to 'identity' so the baseline = pure slide model.
    Each one maps to a violated slide assumption (see PROJECT_HANDOFF.md)."""
    # strain-rate sensitivity of shear strength: tau_s*(1 + c_rate*ln(Vc/Vref))
    c_rate: float = 0.0
    Vref: float = 100.0          # [m/min]
    # speed dependence of friction: mu*(Vc/Vref)**(-m_mu)
    m_mu: float = 0.0
    # size effect on shear strength: tau_s*(t/t_ref)**(-n_size)
    n_size: float = 0.0
    t_ref: float = 0.1           # [mm]
    # edge/ploughing force per unit width (sharp-tool assumption violated) [N/mm]
    Ke_z: float = 0.0
    Ke_xy: float = 0.0
    # shear-angle model overrides
    shear_model: str = "ernst_merchant"
    C_merchant: float = 70.0     # [deg] only for shear_model == "merchant_C"
    k_beta: float = 1.0          # empirical multiplier on beta

# ----------------------------------------------------------- shear angle models
def shear_angle(model, gamma0, eta, C_deg=70.0):
    """Shear angle beta [rad] from the slide relations (all angles in rad)."""
    if model == "ernst_merchant":    # 2beta + eta - gamma0 = pi/2
        return np.pi/4 + gamma0/2 - eta/2
    if model == "lee_shaffer":       # beta + eta - gamma0 = pi/4
        return np.pi/4 + gamma0 - eta
    if model == "stabler":           # beta = pi/4 + gamma0/2 - eta  (as on slide)
        return np.pi/4 + gamma0/2 - eta
    if model == "merchant_C":        # 2beta + eta - gamma0 = C
        return 0.5*(np.radians(C_deg) - eta + gamma0)
    raise ValueError(f"unknown shear model {model!r}")

# --------------------------------------------------------------------- result
@dataclass
class Result:
    beta_deg: float; eta_deg: float; mu_eff: float; tau_eff: float
    Ps: float; PN: float; F: float; N: float; R: float
    Pz: float; Pxy: float; Px: float; Py: float
    r: float; t_chip: float; V_chip: float; V_shear: float; gamma0_deg: float

# ------------------------------------------------------------------ the model
def solve(mat: Material, tool: Tool, cut: Cut, corr: Corrections = Corrections(),
          phi_deg: float = 0.0) -> Result:
    g = np.radians(tool.gamma0_deg)
    # speed / size dependent effective properties (identity when corr is default)
    tau = mat.tau_s * (1 + corr.c_rate*np.log(max(cut.Vc, 1e-9)/corr.Vref)) \
                    * (cut.t/corr.t_ref)**(-corr.n_size)
    mu = tool.mu * (max(cut.Vc, 1e-9)/corr.Vref)**(-corr.m_mu)
    eta = np.arctan(mu)
    beta = corr.k_beta*shear_angle(corr.shear_model, g, eta, corr.C_merchant)
    if not (0 < beta < np.pi/2) or not (beta + eta - g < np.pi/2):
        raise ValueError(f"non-physical shear angle beta={np.degrees(beta):.1f} deg")

    # --- slide: Pz = tau_s w t cos(eta-g) / [sin(beta) cos(beta+eta-g)] ---
    A_shear = cut.w*cut.t/np.sin(beta)              # mm^2 ; tau in MPa -> N
    Ps = tau*A_shear
    R = Ps/np.cos(beta + eta - g)
    Pz = R*np.cos(eta - g) + corr.Ke_z*cut.w
    Pxy = R*np.sin(eta - g) + corr.Ke_xy*cut.w
    # recover force components with the slide transformations
    F = Pz*np.sin(g) + Pxy*np.cos(g)
    N = Pz*np.cos(g) - Pxy*np.sin(g)
    PN = Pz*np.sin(beta) + Pxy*np.cos(beta)
    Ps_chk = Pz*np.cos(beta) - Pxy*np.sin(beta)
    ph = np.radians(phi_deg)
    # kinematics from the velocity hodograph (standard single-shear-plane relations)
    r = np.sin(beta)/np.cos(beta - g)               # t / t_chip
    Vc_ms = cut.Vc/60.0
    return Result(np.degrees(beta), np.degrees(eta), mu, tau, Ps_chk, PN, F, N,
                  float(np.hypot(Pz, Pxy)), Pz, Pxy, Pxy*np.sin(ph), Pxy*np.cos(ph),
                  r, cut.t/r, Vc_ms*r, Vc_ms*np.cos(g)/np.cos(beta - g),
                  tool.gamma0_deg)

# ------------------------------------------------- inverse / calibration helpers
def mu_from_forces(Pz, Pxy, gamma0_deg):
    """Slide: mu_avg = (Pz sin g + Pxy cos g)/(Pz cos g - Pxy sin g)."""
    g = np.radians(gamma0_deg)
    return (Pz*np.sin(g) + Pxy*np.cos(g))/(Pz*np.cos(g) - Pxy*np.sin(g))

def tau_s_from_forces(Pz, Pxy, beta_deg, w, t):
    """Slide: Ps = Pz cos(beta) - Pxy sin(beta); tau_s = Ps sin(beta)/(w t)."""
    b = np.radians(beta_deg)
    return (Pz*np.cos(b) - Pxy*np.sin(b))*np.sin(b)/(w*t)

def beta_from_chip_ratio(r, gamma0_deg):
    """tan(beta) = r cos g/(1 - r sin g), r = t/t_chip."""
    g = np.radians(gamma0_deg)
    return np.degrees(np.arctan(r*np.cos(g)/(1 - r*np.sin(g))))

def specific_coeffs(Pz, Pxy, w, t):
    """Cutting-force coefficients as in lab sheet eq.(5): K = F/(b h)  [N/mm^2 = MPa]."""
    return Pz/(w*t), Pxy/(w*t)
