"""
Modelos de Farmacocinética (PK) y Farmacodinamia (PD).

Implementa modelos de 1, 2 y 3 compartimentos para simulación de
concentración plasmática, modelos PD clásicos (Emax, Hill, inhibición
fraccional) y análisis de órgano aislado (curvas agonista/antagonista
y regresión de Schild). Solo depende de numpy/scipy, sin Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import linregress


# ---------------------------------------------------------------------------
# Resultado PK
# ---------------------------------------------------------------------------

@dataclass
class PKResult:
    """Contenedor de parámetros farmacocinéticos derivados."""

    t: np.ndarray
    c: np.ndarray
    Ke: float = float("nan")
    t_half: float = float("nan")
    Cl: float = float("nan")
    Vd: float = float("nan")
    Cmax: float = float("nan")
    Tmax: float = float("nan")
    auc_numeric: float = float("nan")
    auc_analytic: float = float("nan")
    css_avg: Optional[float] = field(default=None)


# ---------------------------------------------------------------------------
# 1 compartimento — funciones de concentración
# ---------------------------------------------------------------------------

def conc_iv_bolus(t: np.ndarray, dose: float, vd: float, ke: float) -> np.ndarray:
    """IV bolo: C(t) = (Dosis/Vd) * exp(-Ke*t)."""
    t = np.asarray(t, dtype=float)
    return (dose / vd) * np.exp(-ke * t)


def conc_iv_infusion(t: np.ndarray, r0: float, vd: float, ke: float,
                      tinf: float) -> np.ndarray:
    """IV infusión: durante la infusión C(t) = (R0/(Vd*Ke))*(1-exp(-Ke*t));
    tras detenerse en Tinf, C(t) = C(Tinf)*exp(-Ke*(t-Tinf))."""
    t = np.asarray(t, dtype=float)
    c = np.zeros_like(t)
    during = t <= tinf
    after = ~during

    c[during] = (r0 / (vd * ke)) * (1.0 - np.exp(-ke * t[during]))

    c_tinf = (r0 / (vd * ke)) * (1.0 - np.exp(-ke * tinf))
    c[after] = c_tinf * np.exp(-ke * (t[after] - tinf))
    return c


def conc_oral(t: np.ndarray, dose: float, vd: float, ka: float, ke: float,
              f: float = 1.0) -> np.ndarray:
    """Oral/extravascular (absorción de primer orden):
    C(t) = (F*Dosis*Ka)/(Vd*(Ka-Ke)) * (exp(-Ke*t) - exp(-Ka*t)).
    Maneja el caso límite Ka == Ke (flip-flop)."""
    t = np.asarray(t, dtype=float)
    if np.isclose(ka, ke, rtol=1e-9, atol=1e-12):
        return (f * dose * ka / vd) * t * np.exp(-ka * t)
    return (f * dose * ka) / (vd * (ka - ke)) * (np.exp(-ke * t) - np.exp(-ka * t))


def conc_multidose(t: np.ndarray, tau: float, n_doses: int,
                    single_dose_func, **kwargs) -> np.ndarray:
    """Superpone curvas de dosis única desplazadas por k*tau, k=0..n_doses-1
    (solo se incluyen los términos donde t >= k*tau)."""
    t = np.asarray(t, dtype=float)
    c_total = np.zeros_like(t)
    for k in range(n_doses):
        shift = k * tau
        mask = t >= shift
        if not np.any(mask):
            continue
        t_shifted = t[mask] - shift
        c_total[mask] += single_dose_func(t_shifted, **kwargs)
    return c_total


# ---------------------------------------------------------------------------
# Parámetros derivados de 1 compartimento
# ---------------------------------------------------------------------------

def compute_pk_result(t: np.ndarray, c: np.ndarray, dose: float, vd: float,
                       ke: float, route: str, f: float = 1.0,
                       ka: Optional[float] = None,
                       tau: Optional[float] = None,
                       n_doses: Optional[int] = None) -> PKResult:
    """Calcula Ke, t1/2, Cl, Cmax, Tmax, AUC (numérica y analítica) y
    Css_avg (multidosis) a partir de una simulación 1-compartimental."""
    t_half = np.log(2.0) / ke if ke > 0 else float("nan")
    cl = ke * vd

    if route in ("oral", "multidosis_oral") and ka is not None and ka != ke:
        tmax = np.log(ka / ke) / (ka - ke)
        cmax = float(np.max(c))
    elif route in ("oral", "multidosis_oral") and ka is not None:
        tmax = 1.0 / ka
        cmax = float(np.max(c))
    elif route in ("iv_bolo", "multidosis_iv_bolo"):
        tmax = 0.0
        cmax = float(c[0]) if len(c) else float("nan")
    elif route == "infusion":
        # No hay fórmula cerrada simple para Tmax en infusión IV (la
        # concentración crece monótonamente durante la infusión y decae
        # después); se usa la posición numérica del máximo simulado.
        idx = int(np.argmax(c))
        tmax = float(t[idx])
        cmax = float(c[idx])
    else:
        idx = int(np.argmax(c))
        tmax = float(t[idx])
        cmax = float(c[idx])

    auc_numeric = float(np.trapz(c, t))
    auc_analytic = (f * dose / cl) if cl > 0 else float("nan")

    css_avg = None
    if tau is not None and n_doses is not None and n_doses > 0 and cl > 0:
        css_avg = float(f * dose / (cl * tau))

    return PKResult(
        t=t, c=c, Ke=float(ke), t_half=float(t_half), Cl=float(cl),
        Vd=float(vd), Cmax=float(cmax), Tmax=float(tmax),
        auc_numeric=auc_numeric, auc_analytic=float(auc_analytic),
        css_avg=css_avg,
    )


# ---------------------------------------------------------------------------
# 2 compartimentos (IV bolo)
# ---------------------------------------------------------------------------

def conc_2c_from_constants(t: np.ndarray, a: float, alpha: float,
                            b: float, beta: float) -> np.ndarray:
    """Biexponencial: C(t) = A*exp(-alpha*t) + B*exp(-beta*t)."""
    t = np.asarray(t, dtype=float)
    return a * np.exp(-alpha * t) + b * np.exp(-beta * t)


def two_compartment_constants(dose: float, vc: float, k10: float,
                               k12: float, k21: float) -> tuple[float, float, float, float]:
    """Calcula A, alpha, B, beta a partir de Vc, k10, k12, k21 (constantes
    híbridas micro/macro del modelo bicompartimental clásico)."""
    sum_ab = k10 + k12 + k21
    prod_ab = k10 * k21
    disc = sum_ab ** 2 - 4.0 * prod_ab
    sqrt_disc = np.sqrt(disc)
    alpha = (sum_ab + sqrt_disc) / 2.0
    beta = (sum_ab - sqrt_disc) / 2.0

    a = (dose / vc) * (alpha - k21) / (alpha - beta)
    b = (dose / vc) * (k21 - beta) / (alpha - beta)
    return float(a), float(alpha), float(b), float(beta)


# ---------------------------------------------------------------------------
# 3 compartimentos (IV bolo)
# ---------------------------------------------------------------------------

def conc_3c_from_constants(t: np.ndarray, a: float, alpha: float, b: float,
                            beta: float, c: float, gamma: float) -> np.ndarray:
    """Triexponencial: C(t) = A*exp(-alpha*t) + B*exp(-beta*t) + C*exp(-gamma*t)."""
    t = np.asarray(t, dtype=float)
    return (a * np.exp(-alpha * t) + b * np.exp(-beta * t)
            + c * np.exp(-gamma * t))


# ---------------------------------------------------------------------------
# Modelos PD
# ---------------------------------------------------------------------------

def pd_emax(c: np.ndarray, emax: float, ec50: float) -> np.ndarray:
    """Modelo Emax: E = Emax * C / (EC50 + C)."""
    c = np.asarray(c, dtype=float)
    return emax * c / (ec50 + c)


def pd_hill(c: np.ndarray, emax: float, ec50: float, n: float) -> np.ndarray:
    """Hill (Emax sigmoidal): E = Emax * C^n / (EC50^n + C^n)."""
    c = np.asarray(c, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        cn = np.power(c, n)
        return emax * cn / (ec50 ** n + cn)


def pd_fractional_inhibition(c: np.ndarray, imax: float, ic50: float) -> np.ndarray:
    """Inhibición fraccional: I = Imax * C / (IC50 + C)."""
    c = np.asarray(c, dtype=float)
    return imax * c / (ic50 + c)


# ---------------------------------------------------------------------------
# Combinación PK/PD
# ---------------------------------------------------------------------------

def simulate_pkpd(t: np.ndarray, c: np.ndarray, pd_func, **pd_kwargs) -> tuple[np.ndarray, np.ndarray]:
    """Simulación PK/PD combinada asumiendo equilibrio rápido (sin
    compartimento de efecto / histéresis): E(t) = PD(C(t))."""
    e = pd_func(c, **pd_kwargs)
    return t, e


# ---------------------------------------------------------------------------
# Órgano aislado / Análisis de Schild
# ---------------------------------------------------------------------------

def agonist_response(a: np.ndarray, ec50: float, n: float, emax: float) -> np.ndarray:
    """Curva agonista sola: E = Emax * A^n / (EC50^n + A^n)."""
    a = np.asarray(a, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        an = np.power(a, n)
        return emax * an / (ec50 ** n + an)


def dose_ratio(b_conc: float, kb: float) -> float:
    """Razón de dosis para un antagonista competitivo: DR = 1 + B/KB."""
    return 1.0 + (b_conc / kb)


def antagonist_shifted_response(a: np.ndarray, ec50: float, n: float,
                                 emax: float, b_conc: float, kb: float) -> np.ndarray:
    """Curva agonista desplazada por antagonista competitivo:
    E = Emax * A^n / ((EC50*DR)^n + A^n), con DR = 1 + B/KB."""
    dr = dose_ratio(b_conc, kb)
    a = np.asarray(a, dtype=float)
    ec50_shifted = ec50 * dr
    with np.errstate(invalid="ignore", divide="ignore"):
        an = np.power(a, n)
        return emax * an / (ec50_shifted ** n + an)


def simulate_schild(agonist_concentrations: np.ndarray, ec50: float, n: float,
                     emax: float, antagonist_concentrations: np.ndarray,
                     kb: float) -> tuple[list[np.ndarray], np.ndarray]:
    """Para cada concentración de antagonista, devuelve la curva agonista
    desplazada (para graficar superpuesta) y la razón de dosis (DR)."""
    curves: list[np.ndarray] = []
    dose_ratios = np.zeros(len(antagonist_concentrations))
    for i, b_conc in enumerate(antagonist_concentrations):
        if b_conc <= 0:
            curve = agonist_response(agonist_concentrations, ec50, n, emax)
            dose_ratios[i] = 1.0
        else:
            curve = antagonist_shifted_response(
                agonist_concentrations, ec50, n, emax, b_conc, kb
            )
            dose_ratios[i] = dose_ratio(b_conc, kb)
        curves.append(curve)
    return curves, dose_ratios


@dataclass
class SchildResult:
    """Resultado de la regresión de Schild."""

    slope: float
    intercept: float
    pA2: float
    r_value: float
    KB: float


def schild_regression(antagonist_concentrations: np.ndarray,
                       dose_ratios: np.ndarray) -> SchildResult:
    """Regresión lineal de log10(DR-1) vs log10([B]).
    pA2 = -intercept/slope (general); si slope≈1, pA2 ≈ -intercept.
    KB = 10^(-pA2)."""
    b = np.asarray(antagonist_concentrations, dtype=float)
    dr = np.asarray(dose_ratios, dtype=float)

    mask = (b > 0) & (dr > 1.0)
    log_b = np.log10(b[mask])
    log_dr_minus_1 = np.log10(dr[mask] - 1.0)

    result = linregress(log_b, log_dr_minus_1)
    slope, intercept, r_value = result.slope, result.intercept, result.rvalue

    pa2 = -intercept / slope if slope != 0 else float("nan")
    kb = 10.0 ** (-pa2)

    return SchildResult(
        slope=float(slope), intercept=float(intercept),
        pA2=float(pa2), r_value=float(r_value), KB=float(kb),
    )


def pD2(ec50: float) -> float:
    """Potencia del agonista solo: pD2 = -log10(EC50)."""
    return float(-np.log10(ec50))
