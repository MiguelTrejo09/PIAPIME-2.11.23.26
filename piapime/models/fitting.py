"""
Modelos de ajuste de curvas dosis-respuesta.

Implementa modelos 4PL, 3PL, 2PL y Ecuación de Hill para análisis
de datos dosis-respuesta en farmacología y bioquímica.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t as t_dist


# ---------------------------------------------------------------------------
# Resultado del ajuste
# ---------------------------------------------------------------------------

@dataclass
class FittingResult:
    """Contenedor con todos los resultados del ajuste de curva."""

    model_name: str
    parameters: dict  # {nombre: valor}
    param_errors: dict  # {nombre: error_estándar}
    ci_95: dict  # {nombre: (inferior, superior)}
    ec50: float
    ec50_ci: tuple  # (inferior, superior)
    r_squared: float
    rmse: float
    aic: float
    bic: float
    x_fit: np.ndarray  # x para curva ajustada (escala lineal)
    y_fit: np.ndarray  # y para curva ajustada
    residuals: np.ndarray
    success: bool
    message: str
    # CI banda (bootstrap)
    y_fit_lower: Optional[np.ndarray] = field(default=None)
    y_fit_upper: Optional[np.ndarray] = field(default=None)


# ---------------------------------------------------------------------------
# Funciones de los modelos
# ---------------------------------------------------------------------------

def _model_4pl(x: np.ndarray, bottom: float, top: float,
               log_ec50: float, hill: float) -> np.ndarray:
    """Modelo logístico de 4 parámetros (4PL).

    y = Bottom + (Top - Bottom) / (1 + 10^(HillSlope * (LogEC50 - log10(x))))
    """
    with np.errstate(over="ignore", invalid="ignore"):
        exponent = hill * (log_ec50 - np.log10(np.clip(x, 1e-300, None)))
        denom = 1.0 + np.power(10.0, np.clip(exponent, -500, 500))
        return bottom + (top - bottom) / denom


def _model_3pl(x: np.ndarray, top: float, log_ec50: float,
               hill: float) -> np.ndarray:
    """Modelo logístico de 3 parámetros (3PL). Bottom fijo en 0."""
    with np.errstate(over="ignore", invalid="ignore"):
        exponent = hill * (log_ec50 - np.log10(np.clip(x, 1e-300, None)))
        denom = 1.0 + np.power(10.0, np.clip(exponent, -500, 500))
        return top / denom


def _model_2pl(x: np.ndarray, log_ec50: float, hill: float) -> np.ndarray:
    """Modelo logístico de 2 parámetros (2PL). Bottom=0, Top=100."""
    with np.errstate(over="ignore", invalid="ignore"):
        exponent = hill * (log_ec50 - np.log10(np.clip(x, 1e-300, None)))
        denom = 1.0 + np.power(10.0, np.clip(exponent, -500, 500))
        return 100.0 / denom


def _model_hill(x: np.ndarray, bottom: float, top: float,
                log_ec50: float, hill: float) -> np.ndarray:
    """Ecuación de Hill (equivalente al 4PL, nomenclatura farmacológica)."""
    return _model_4pl(x, bottom, top, log_ec50, hill)


# ---------------------------------------------------------------------------
# Metadatos de los modelos
# ---------------------------------------------------------------------------

MODEL_REGISTRY = {
    "4PL": {
        "func": _model_4pl,
        "param_names": ["Bottom", "Top", "LogEC50", "HillSlope"],
        "display_names": ["Bottom", "Top", "LogEC50", "HillSlope"],
    },
    "3PL": {
        "func": _model_3pl,
        "param_names": ["Top", "LogEC50", "HillSlope"],
        "display_names": ["Top", "LogEC50", "HillSlope"],
    },
    "2PL": {
        "func": _model_2pl,
        "param_names": ["LogEC50", "HillSlope"],
        "display_names": ["LogEC50", "HillSlope"],
    },
    "Hill": {
        "func": _model_hill,
        "param_names": ["Bottom", "Top", "LogEC50", "HillSlope"],
        "display_names": ["Bottom", "Top", "LogEC50", "HillSlope"],
    },
}

# Nombres amigables → clave interna
MODEL_NAME_MAP = {
    "4PL (4-Parámetros Logístico)": "4PL",
    "3PL (3-Parámetros Logístico)": "3PL",
    "2PL (2-Parámetros Logístico)": "2PL",
    "Ecuación de Hill": "Hill",
}


# ---------------------------------------------------------------------------
# Ajustador principal
# ---------------------------------------------------------------------------

class DoseResponseFitter:
    """Realiza el ajuste de curvas dosis-respuesta con estadísticas completas."""

    def __init__(self) -> None:
        self._max_fev = 10_000

    # ------------------------------------------------------------------
    # Estimación de parámetros iniciales
    # ------------------------------------------------------------------

    def _estimate_initial_params(self, x: np.ndarray, y: np.ndarray,
                                 model_key: str) -> list[float]:
        """Estima parámetros iniciales robustos a partir de los datos."""
        bottom_est = float(np.min(y))
        top_est = float(np.max(y))
        # Proteger contra x == 0
        x_pos = x[x > 0]
        log_ec50_est = float(np.mean(np.log10(x_pos))) if len(x_pos) > 0 else 0.0
        hill_est = 1.0

        if model_key in ("4PL", "Hill"):
            return [bottom_est, top_est, log_ec50_est, hill_est]
        elif model_key == "3PL":
            return [top_est, log_ec50_est, hill_est]
        elif model_key == "2PL":
            return [log_ec50_est, hill_est]
        return [log_ec50_est, hill_est]

    # ------------------------------------------------------------------
    # Estadísticas de bondad de ajuste
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_r_squared(y_obs: np.ndarray, y_pred: np.ndarray) -> float:
        ss_res = np.sum((y_obs - y_pred) ** 2)
        ss_tot = np.sum((y_obs - np.mean(y_obs)) ** 2)
        if ss_tot == 0:
            return 1.0 if ss_res == 0 else 0.0
        return float(1.0 - ss_res / ss_tot)

    @staticmethod
    def _compute_rmse(y_obs: np.ndarray, y_pred: np.ndarray) -> float:
        return float(np.sqrt(np.mean((y_obs - y_pred) ** 2)))

    @staticmethod
    def _compute_aic_bic(y_obs: np.ndarray, y_pred: np.ndarray,
                         n_params: int) -> tuple[float, float]:
        n = len(y_obs)
        residuals = y_obs - y_pred
        sse = np.sum(residuals ** 2)
        if sse <= 0 or n <= n_params:
            return float("nan"), float("nan")
        sigma2 = sse / n
        log_lik = -n / 2.0 * np.log(2 * np.pi * sigma2) - sse / (2 * sigma2)
        aic = 2 * n_params - 2 * log_lik
        bic = n_params * np.log(n) - 2 * log_lik
        return float(aic), float(bic)

    # ------------------------------------------------------------------
    # Intervalos de confianza por t-distribución (paramétricos)
    # ------------------------------------------------------------------

    @staticmethod
    def _param_ci(popt: np.ndarray, pcov: np.ndarray,
                  n_obs: int, alpha: float = 0.05) -> list[tuple[float, float]]:
        n_params = len(popt)
        dof = max(n_obs - n_params, 1)
        t_val = t_dist.ppf(1.0 - alpha / 2.0, dof)
        perr = np.sqrt(np.diag(pcov))
        return [(float(p - t_val * e), float(p + t_val * e))
                for p, e in zip(popt, perr)]

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def bootstrap_ci(self, x: np.ndarray, y: np.ndarray,
                     model_key: str, params: list[float],
                     n_bootstrap: int = 500) -> dict:
        """Calcula CI del 95% por bootstrap residual."""
        func = MODEL_REGISTRY[model_key]["func"]
        param_names = MODEL_REGISTRY[model_key]["param_names"]

        y_pred = func(x, *params)
        residuals = y - y_pred

        boot_params: list[list[float]] = []
        rng = np.random.default_rng(42)

        for _ in range(n_bootstrap):
            y_boot = y_pred + rng.choice(residuals, size=len(residuals), replace=True)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    p0 = self._estimate_initial_params(x, y_boot, model_key)
                    popt_b, _ = curve_fit(func, x, y_boot, p0=p0,
                                          maxfev=self._max_fev)
                boot_params.append(list(popt_b))
            except Exception:
                pass

        if not boot_params:
            return {name: (float("nan"), float("nan")) for name in param_names}

        boot_arr = np.array(boot_params)
        ci = {}
        for i, name in enumerate(param_names):
            lo = float(np.percentile(boot_arr[:, i], 2.5))
            hi = float(np.percentile(boot_arr[:, i], 97.5))
            ci[name] = (lo, hi)

        return ci

    def _bootstrap_curve_band(self, x: np.ndarray, y: np.ndarray,
                               model_key: str, params: list[float],
                               x_fit: np.ndarray,
                               n_bootstrap: int = 500) -> tuple[np.ndarray, np.ndarray]:
        """Devuelve banda inferior y superior de la curva ajustada via bootstrap."""
        func = MODEL_REGISTRY[model_key]["func"]
        y_pred = func(x, *params)
        residuals = y - y_pred

        boot_curves = []
        rng = np.random.default_rng(42)

        for _ in range(n_bootstrap):
            y_boot = y_pred + rng.choice(residuals, size=len(residuals), replace=True)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    p0 = self._estimate_initial_params(x, y_boot, model_key)
                    popt_b, _ = curve_fit(func, x, y_boot, p0=p0,
                                          maxfev=self._max_fev)
                boot_curves.append(func(x_fit, *popt_b))
            except Exception:
                pass

        if not boot_curves:
            y_fit = func(x_fit, *params)
            return y_fit, y_fit

        curves_arr = np.array(boot_curves)
        lower = np.percentile(curves_arr, 2.5, axis=0)
        upper = np.percentile(curves_arr, 97.5, axis=0)
        return lower, upper

    # ------------------------------------------------------------------
    # Ajuste principal
    # ------------------------------------------------------------------

    def fit(self, x: np.ndarray, y: np.ndarray, model_name: str,
            initial_params: Optional[list[float]] = None,
            do_bootstrap: bool = True,
            n_bootstrap: int = 500) -> FittingResult:
        """Ajusta el modelo al conjunto de datos y devuelve FittingResult completo."""

        # Resolver nombre de modelo
        model_key = MODEL_NAME_MAP.get(model_name, model_name)
        if model_key not in MODEL_REGISTRY:
            return FittingResult(
                model_name=model_name,
                parameters={}, param_errors={}, ci_95={},
                ec50=float("nan"), ec50_ci=(float("nan"), float("nan")),
                r_squared=float("nan"), rmse=float("nan"),
                aic=float("nan"), bic=float("nan"),
                x_fit=np.array([]), y_fit=np.array([]),
                residuals=np.array([]),
                success=False,
                message=f"Modelo desconocido: {model_name}",
            )

        info = MODEL_REGISTRY[model_key]
        func = info["func"]
        param_names = info["param_names"]

        # Filtrar datos inválidos
        mask = np.isfinite(x) & np.isfinite(y) & (x > 0)
        x_clean = x[mask].astype(float)
        y_clean = y[mask].astype(float)

        if len(x_clean) < len(param_names) + 1:
            return FittingResult(
                model_name=model_name,
                parameters={}, param_errors={}, ci_95={},
                ec50=float("nan"), ec50_ci=(float("nan"), float("nan")),
                r_squared=float("nan"), rmse=float("nan"),
                aic=float("nan"), bic=float("nan"),
                x_fit=np.array([]), y_fit=np.array([]),
                residuals=np.array([]),
                success=False,
                message="Datos insuficientes para el ajuste.",
            )

        # Parámetros iniciales
        if initial_params is None:
            p0 = self._estimate_initial_params(x_clean, y_clean, model_key)
        else:
            p0 = list(initial_params)

        # Intentar ajuste con múltiples estrategias
        popt, pcov = None, None
        last_error = ""
        for attempt_p0 in [p0, self._estimate_initial_params(x_clean, y_clean, model_key)]:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    popt, pcov = curve_fit(
                        func, x_clean, y_clean,
                        p0=attempt_p0,
                        maxfev=self._max_fev,
                        method="trf",
                    )
                break
            except Exception as e:
                last_error = str(e)
                popt, pcov = None, None

        if popt is None:
            return FittingResult(
                model_name=model_name,
                parameters={}, param_errors={}, ci_95={},
                ec50=float("nan"), ec50_ci=(float("nan"), float("nan")),
                r_squared=float("nan"), rmse=float("nan"),
                aic=float("nan"), bic=float("nan"),
                x_fit=np.array([]), y_fit=np.array([]),
                residuals=np.array([]),
                success=False,
                message=f"El ajuste no convergió: {last_error}",
            )

        # Verificar covarianza válida
        try:
            perr = np.sqrt(np.diag(pcov))
            if not np.all(np.isfinite(perr)):
                perr = np.full(len(popt), float("nan"))
        except Exception:
            perr = np.full(len(popt), float("nan"))

        # Estadísticas
        y_pred = func(x_clean, *popt)
        residuals = y_clean - y_pred
        r2 = self._compute_r_squared(y_clean, y_pred)
        rmse = self._compute_rmse(y_clean, y_pred)
        aic, bic = self._compute_aic_bic(y_clean, y_pred, len(popt))

        # CI paramétrico (t-distribución)
        try:
            ci_list = self._param_ci(popt, pcov, len(x_clean))
        except Exception:
            ci_list = [(float("nan"), float("nan"))] * len(popt)

        parameters = {name: float(val) for name, val in zip(param_names, popt)}
        param_errors = {name: float(e) for name, e in zip(param_names, perr)}
        ci_95 = {name: ci_list[i] for i, name in enumerate(param_names)}

        # EC50
        if "LogEC50" in parameters:
            ec50 = float(10.0 ** parameters["LogEC50"])
            lo_ci, hi_ci = ci_95["LogEC50"]
            ec50_ci = (float(10.0 ** lo_ci) if np.isfinite(lo_ci) else float("nan"),
                       float(10.0 ** hi_ci) if np.isfinite(hi_ci) else float("nan"))
        else:
            ec50 = float("nan")
            ec50_ci = (float("nan"), float("nan"))

        # Curva ajustada (500 puntos en escala log)
        x_min = np.min(x_clean) / 10.0
        x_max = np.max(x_clean) * 10.0
        x_fit = np.logspace(np.log10(x_min), np.log10(x_max), 500)
        y_fit = func(x_fit, *popt)

        # Bootstrap (opcional)
        y_fit_lower = None
        y_fit_upper = None
        if do_bootstrap:
            try:
                boot_ci = self.bootstrap_ci(x_clean, y_clean, model_key,
                                             list(popt), n_bootstrap)
                ci_95.update(boot_ci)
                # Actualizar EC50 CI con bootstrap
                if "LogEC50" in boot_ci:
                    lo_b, hi_b = boot_ci["LogEC50"]
                    ec50_ci = (float(10.0 ** lo_b) if np.isfinite(lo_b) else ec50_ci[0],
                               float(10.0 ** hi_b) if np.isfinite(hi_b) else ec50_ci[1])
                lower_band, upper_band = self._bootstrap_curve_band(
                    x_clean, y_clean, model_key, list(popt), x_fit, n_bootstrap
                )
                y_fit_lower = lower_band
                y_fit_upper = upper_band
            except Exception:
                pass

        return FittingResult(
            model_name=model_name,
            parameters=parameters,
            param_errors=param_errors,
            ci_95=ci_95,
            ec50=ec50,
            ec50_ci=ec50_ci,
            r_squared=r2,
            rmse=rmse,
            aic=aic,
            bic=bic,
            x_fit=x_fit,
            y_fit=y_fit,
            residuals=residuals,
            success=True,
            message="Ajuste completado exitosamente.",
            y_fit_lower=y_fit_lower,
            y_fit_upper=y_fit_upper,
        )
