"""Panel de Farmacocinética / Farmacodinamia (PK/PD)."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QPushButton, QDoubleSpinBox, QSpinBox, QGroupBox, QTabWidget,
    QScrollArea, QFrame, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QMessageBox,
)

from piapime.pkpd import models as pk


def _fmt(value, decimals: int = 4) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "N/A"
    if abs(value) < 1e-3 and value != 0 or abs(value) > 1e6:
        return f"{value:.4e}"
    return f"{value:.{decimals}f}"


def _new_canvas(figsize=(7, 5)):
    """Crea un canvas matplotlib embebido siguiendo el estilo de PlotPanel."""
    fig = Figure(figsize=figsize, dpi=100, facecolor="#1e1e2e")
    canvas = FigureCanvasQTAgg(fig)
    canvas.setMinimumHeight(320)
    toolbar = NavigationToolbar2QT(canvas, None)
    toolbar.setStyleSheet(
        "QToolBar { background: #181825; border: none; }"
        "QToolButton { color: #cdd6f4; background: transparent; border: none; padding: 4px; }"
        "QToolButton:hover { background: #313244; border-radius: 4px; }"
    )
    return fig, canvas, toolbar


def _style_axes(fig: Figure, *axes) -> None:
    bg = "#1e1e2e"
    fg = "#cdd6f4"
    fig.patch.set_facecolor(bg)
    for ax in axes:
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#45475a")
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
        ax.title.set_color(fg)
        ax.grid(True, color="#313244", linewidth=0.7, linestyle="--", alpha=0.7)


# ---------------------------------------------------------------------------
# Sub-pestaña A: Farmacocinética
# ---------------------------------------------------------------------------

_ROUTES = [
    "IV Bolo", "IV Infusión", "Oral/Extravascular",
    "Multidosis Oral", "Multidosis IV Bolo",
]
_COMPARTMENTS = ["1 compartimento", "2 compartimentos", "3 compartimentos"]


class _PKSubTab(QWidget):
    """Sub-pestaña de simulación farmacocinética (1/2/3 compartimentos)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.last_t: Optional[np.ndarray] = None
        self.last_c: Optional[np.ndarray] = None
        self._setup_ui()
        self._on_route_changed(self._route_combo.currentText())
        self._on_compartments_changed(self._comp_combo.currentText())

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # ── Panel de formulario (izquierda) ─────────────────────────
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_scroll.setMaximumWidth(360)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(8)

        title = QLabel("Simulación Farmacocinética")
        title.setObjectName("labelTitle")
        form_layout.addWidget(title)

        route_group = QGroupBox("Vía de Administración / Compartimentos")
        route_form = QFormLayout(route_group)

        self._route_combo = QComboBox()
        self._route_combo.addItems(_ROUTES)
        self._route_combo.currentTextChanged.connect(self._on_route_changed)
        route_form.addRow("Vía:", self._route_combo)

        self._comp_combo = QComboBox()
        self._comp_combo.addItems(_COMPARTMENTS)
        self._comp_combo.currentTextChanged.connect(self._on_compartments_changed)
        route_form.addRow("Compartimentos:", self._comp_combo)
        form_layout.addWidget(route_group)

        # ── Parámetros 1-compartimento ──────────────────────────────
        self._group_1c = QGroupBox("Parámetros (1 Compartimento)")
        f1 = QFormLayout(self._group_1c)

        self._sb_dose = self._make_spin(0.0, 1e6, 100.0, 2)
        f1.addRow("Dosis (mg):", self._sb_dose)

        self._sb_vd = self._make_spin(0.001, 1e6, 50.0, 3)
        f1.addRow("Vd (L):", self._sb_vd)

        self._sb_ke = self._make_spin(0.0001, 100.0, 0.1, 4)
        f1.addRow("Ke (1/h):", self._sb_ke)

        self._sb_ka = self._make_spin(0.0001, 100.0, 1.0, 4)
        f1.addRow("Ka (1/h):", self._sb_ka)

        self._sb_f = self._make_spin(0.0, 1.0, 1.0, 3)
        f1.addRow("F (biodisponibilidad):", self._sb_f)

        self._sb_r0 = self._make_spin(0.0, 1e6, 50.0, 3)
        f1.addRow("R0 (mg/h):", self._sb_r0)

        self._sb_tinf = self._make_spin(0.01, 1000.0, 1.0, 3)
        f1.addRow("Tinf (h):", self._sb_tinf)

        self._sb_tau = self._make_spin(0.1, 1000.0, 8.0, 3)
        f1.addRow("Tau (h):", self._sb_tau)

        self._sb_ndoses = QSpinBox()
        self._sb_ndoses.setRange(1, 100)
        self._sb_ndoses.setValue(5)
        f1.addRow("N° de dosis:", self._sb_ndoses)

        form_layout.addWidget(self._group_1c)

        # ── Parámetros 2-compartimentos ─────────────────────────────
        self._group_2c = QGroupBox("Parámetros (2 Compartimentos)")
        f2 = QFormLayout(self._group_2c)

        self._chk_2c_constants = QCheckBox("Ingresar A, alpha, B, beta directamente")
        self._chk_2c_constants.setChecked(True)
        self._chk_2c_constants.toggled.connect(self._on_2c_mode_changed)
        f2.addRow(self._chk_2c_constants)

        self._sb_a = self._make_spin(-1e6, 1e6, 5.0, 4)
        f2.addRow("A:", self._sb_a)
        self._sb_alpha = self._make_spin(0.0001, 100.0, 2.0, 4)
        f2.addRow("alpha (1/h):", self._sb_alpha)
        self._sb_b = self._make_spin(-1e6, 1e6, 2.0, 4)
        f2.addRow("B:", self._sb_b)
        self._sb_beta = self._make_spin(0.0001, 100.0, 0.2, 4)
        f2.addRow("beta (1/h):", self._sb_beta)

        self._sb_vc = self._make_spin(0.001, 1e6, 10.0, 3)
        f2.addRow("Vc (L):", self._sb_vc)
        self._sb_k10 = self._make_spin(0.0001, 100.0, 0.3, 4)
        f2.addRow("k10 (1/h):", self._sb_k10)
        self._sb_k12 = self._make_spin(0.0001, 100.0, 0.2, 4)
        f2.addRow("k12 (1/h):", self._sb_k12)
        self._sb_k21 = self._make_spin(0.0001, 100.0, 0.1, 4)
        f2.addRow("k21 (1/h):", self._sb_k21)

        form_layout.addWidget(self._group_2c)
        self._group_2c.setVisible(False)

        # ── Parámetros 3-compartimentos ─────────────────────────────
        self._group_3c = QGroupBox("Parámetros (3 Compartimentos)")
        f3 = QFormLayout(self._group_3c)

        self._sb_a3 = self._make_spin(-1e6, 1e6, 8.0, 4)
        f3.addRow("A:", self._sb_a3)
        self._sb_alpha3 = self._make_spin(0.0001, 100.0, 3.0, 4)
        f3.addRow("alpha (1/h):", self._sb_alpha3)
        self._sb_b3 = self._make_spin(-1e6, 1e6, 3.0, 4)
        f3.addRow("B:", self._sb_b3)
        self._sb_beta3 = self._make_spin(0.0001, 100.0, 0.5, 4)
        f3.addRow("beta (1/h):", self._sb_beta3)
        self._sb_c3 = self._make_spin(-1e6, 1e6, 1.0, 4)
        f3.addRow("C:", self._sb_c3)
        self._sb_gamma3 = self._make_spin(0.0001, 100.0, 0.05, 4)
        f3.addRow("gamma (1/h):", self._sb_gamma3)

        form_layout.addWidget(self._group_3c)
        self._group_3c.setVisible(False)

        # ── Tiempo de simulación ─────────────────────────────────────
        time_group = QGroupBox("Tiempo de Simulación")
        time_form = QFormLayout(time_group)
        self._sb_tmax = self._make_spin(0.1, 10000.0, 24.0, 2)
        time_form.addRow("Tiempo máximo (h):", self._sb_tmax)
        form_layout.addWidget(time_group)

        self._btn_simulate = QPushButton("Simular")
        self._btn_simulate.setObjectName("btnFit")
        self._btn_simulate.clicked.connect(self._on_simulate)
        form_layout.addWidget(self._btn_simulate)

        # ── Resultados ────────────────────────────────────────────────
        results_group = QGroupBox("Resultados")
        results_form = QFormLayout(results_group)
        self._lbl_ke = QLabel("N/A")
        self._lbl_thalf = QLabel("N/A")
        self._lbl_cl = QLabel("N/A")
        self._lbl_cmax = QLabel("N/A")
        self._lbl_tmax = QLabel("N/A")
        self._lbl_auc_num = QLabel("N/A")
        self._lbl_auc_an = QLabel("N/A")
        self._lbl_css = QLabel("N/A")
        results_form.addRow("Ke:", self._lbl_ke)
        results_form.addRow("t½ (h):", self._lbl_thalf)
        results_form.addRow("Cl (L/h):", self._lbl_cl)
        results_form.addRow("Cmax:", self._lbl_cmax)
        results_form.addRow("Tmax (h):", self._lbl_tmax)
        results_form.addRow("AUC numérica:", self._lbl_auc_num)
        results_form.addRow("AUC analítica:", self._lbl_auc_an)
        results_form.addRow("Css promedio:", self._lbl_css)
        form_layout.addWidget(results_group)

        form_layout.addStretch()
        form_scroll.setWidget(form_container)
        main_layout.addWidget(form_scroll)

        # ── Canvas (derecha) ─────────────────────────────────────────
        right_layout = QVBoxLayout()
        self._fig, self._canvas, self._toolbar = _new_canvas()
        self._ax = self._fig.add_subplot(111)
        _style_axes(self._fig, self._ax)
        self._fig.subplots_adjust(left=0.12, right=0.96, top=0.92, bottom=0.12)
        right_layout.addWidget(self._toolbar)
        right_layout.addWidget(self._canvas)
        main_layout.addLayout(right_layout)

    @staticmethod
    def _make_spin(lo: float, hi: float, default: float, decimals: int) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setDecimals(decimals)
        sb.setValue(default)
        sb.setSingleStep(10 ** (-decimals + 1) if decimals > 0 else 1.0)
        return sb

    # ------------------------------------------------------------------
    # Visibilidad dinámica de parámetros
    # ------------------------------------------------------------------

    def _on_route_changed(self, route: str) -> None:
        is_oral = route in ("Oral/Extravascular", "Multidosis Oral")
        is_infusion = route == "IV Infusión"
        is_multi = route in ("Multidosis Oral", "Multidosis IV Bolo")

        for sb, visible in [
            (self._sb_dose, not is_infusion),
            (self._sb_ka, is_oral), (self._sb_f, is_oral),
            (self._sb_r0, is_infusion), (self._sb_tinf, is_infusion),
            (self._sb_tau, is_multi), (self._sb_ndoses, is_multi),
        ]:
            sb.setEnabled(visible)
            sb.setVisible(visible)
            label = self._group_1c.layout().labelForField(sb)
            if label is not None:
                label.setVisible(visible)

    def _on_compartments_changed(self, comp: str) -> None:
        self._group_1c.setVisible(comp == "1 compartimento")
        self._group_2c.setVisible(comp == "2 compartimentos")
        self._group_3c.setVisible(comp == "3 compartimentos")
        if comp != "1 compartimento":
            self._route_combo.setCurrentText("IV Bolo")
            self._route_combo.setEnabled(False)
        else:
            self._route_combo.setEnabled(True)
        self._on_2c_mode_changed(self._chk_2c_constants.isChecked())

    def _on_2c_mode_changed(self, use_constants: bool) -> None:
        for sb in (self._sb_a, self._sb_alpha, self._sb_b, self._sb_beta):
            sb.setEnabled(use_constants)
        for sb in (self._sb_vc, self._sb_k10, self._sb_k12, self._sb_k21):
            sb.setEnabled(not use_constants)

    # ------------------------------------------------------------------
    # Simulación
    # ------------------------------------------------------------------

    def _on_simulate(self) -> None:
        comp = self._comp_combo.currentText()
        tmax = self._sb_tmax.value()
        t = np.linspace(0.0, tmax, 1000)

        try:
            if comp == "1 compartimento":
                t, c, pk_result = self._simulate_1c(t)
            elif comp == "2 compartimentos":
                t, c, pk_result = self._simulate_2c(t)
            else:
                t, c, pk_result = self._simulate_3c(t)
        except Exception as e:
            QMessageBox.critical(self, "Error de simulación", str(e))
            return

        self.last_t = t
        self.last_c = c
        self._plot(t, c)
        self._update_results_labels(pk_result)

    def _simulate_1c(self, t: np.ndarray):
        route = self._route_combo.currentText()
        dose = self._sb_dose.value()
        vd = self._sb_vd.value()
        ke = self._sb_ke.value()
        ka = self._sb_ka.value()
        f = self._sb_f.value()
        r0 = self._sb_r0.value()
        tinf = self._sb_tinf.value()
        tau = self._sb_tau.value()
        n_doses = self._sb_ndoses.value()

        route_key = None
        if route == "IV Bolo":
            c = pk.conc_iv_bolus(t, dose, vd, ke)
            route_key = "iv_bolo"
        elif route == "IV Infusión":
            c = pk.conc_iv_infusion(t, r0, vd, ke, tinf)
            route_key = "infusion"
        elif route == "Oral/Extravascular":
            c = pk.conc_oral(t, dose, vd, ka, ke, f)
            route_key = "oral"
        elif route == "Multidosis Oral":
            c = pk.conc_multidose(t, tau, n_doses, pk.conc_oral,
                                   dose=dose, vd=vd, ka=ka, ke=ke, f=f)
            route_key = "multidosis_oral"
        else:  # Multidosis IV Bolo
            c = pk.conc_multidose(t, tau, n_doses, pk.conc_iv_bolus,
                                   dose=dose, vd=vd, ke=ke)
            route_key = "multidosis_iv_bolo"

        # Para infusión IV, la dosis total administrada es R0*Tinf, no el
        # campo "Dosis" (que solo aplica a bolo/oral/multidosis).
        dose_for_auc = r0 * tinf if route_key == "infusion" else dose

        result = pk.compute_pk_result(
            t, c, dose_for_auc, vd, ke, route_key, f=f,
            ka=ka if route_key in ("oral", "multidosis_oral") else None,
            tau=tau if "multidosis" in route_key else None,
            n_doses=n_doses if "multidosis" in route_key else None,
        )
        return t, c, result

    def _simulate_2c(self, t: np.ndarray):
        if self._chk_2c_constants.isChecked():
            a, alpha, b, beta = (self._sb_a.value(), self._sb_alpha.value(),
                                 self._sb_b.value(), self._sb_beta.value())
        else:
            dose = self._sb_dose.value()
            vc = self._sb_vc.value()
            k10 = self._sb_k10.value()
            k12 = self._sb_k12.value()
            k21 = self._sb_k21.value()
            a, alpha, b, beta = pk.two_compartment_constants(dose, vc, k10, k12, k21)

        c = pk.conc_2c_from_constants(t, a, alpha, b, beta)
        ke_eff = beta  # constante de eliminación terminal (beta) como aproximación
        result = pk.PKResult(
            t=t, c=c, Ke=ke_eff, t_half=math.log(2.0) / beta if beta > 0 else float("nan"),
            Cl=float("nan"), Vd=float("nan"),
            Cmax=float(c[0]), Tmax=0.0,
            auc_numeric=float(np.trapz(c, t)), auc_analytic=float("nan"),
            css_avg=None,
        )
        return t, c, result

    def _simulate_3c(self, t: np.ndarray):
        a, alpha = self._sb_a3.value(), self._sb_alpha3.value()
        b, beta = self._sb_b3.value(), self._sb_beta3.value()
        c3, gamma = self._sb_c3.value(), self._sb_gamma3.value()

        c = pk.conc_3c_from_constants(t, a, alpha, b, beta, c3, gamma)
        result = pk.PKResult(
            t=t, c=c, Ke=gamma,
            t_half=math.log(2.0) / gamma if gamma > 0 else float("nan"),
            Cl=float("nan"), Vd=float("nan"),
            Cmax=float(c[0]), Tmax=0.0,
            auc_numeric=float(np.trapz(c, t)), auc_analytic=float("nan"),
            css_avg=None,
        )
        return t, c, result

    def _update_results_labels(self, r: pk.PKResult) -> None:
        self._lbl_ke.setText(_fmt(r.Ke))
        self._lbl_thalf.setText(_fmt(r.t_half))
        self._lbl_cl.setText(_fmt(r.Cl))
        self._lbl_cmax.setText(_fmt(r.Cmax))
        self._lbl_tmax.setText(_fmt(r.Tmax))
        self._lbl_auc_num.setText(_fmt(r.auc_numeric))
        self._lbl_auc_an.setText(_fmt(r.auc_analytic))
        self._lbl_css.setText(_fmt(r.css_avg) if r.css_avg is not None else "N/A")

    def _plot(self, t: np.ndarray, c: np.ndarray) -> None:
        self._ax.clear()
        self._ax.plot(t, c, color="#89b4fa", linewidth=2)
        self._ax.set_xlabel("Tiempo (h)")
        self._ax.set_ylabel("Concentración plasmática")
        self._ax.set_title("Curva Concentración vs. Tiempo")
        _style_axes(self._fig, self._ax)
        self._canvas.draw()


# ---------------------------------------------------------------------------
# Sub-pestaña B: Farmacodinamia
# ---------------------------------------------------------------------------

_PD_MODELS = ["Emax", "Hill (Emax sigmoidal)", "Inhibición fraccional"]


class _PDSubTab(QWidget):
    """Sub-pestaña de simulación farmacodinámica, opcionalmente acoplada a PK."""

    def __init__(self, pk_subtab: _PKSubTab, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pk_subtab = pk_subtab
        self._setup_ui()
        self._on_model_changed(self._model_combo.currentText())

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        form_container = QWidget()
        form_container.setMaximumWidth(340)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(8)

        title = QLabel("Simulación Farmacodinámica")
        title.setObjectName("labelTitle")
        form_layout.addWidget(title)

        model_group = QGroupBox("Modelo PD")
        model_form = QFormLayout(model_group)
        self._model_combo = QComboBox()
        self._model_combo.addItems(_PD_MODELS)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        model_form.addRow("Modelo:", self._model_combo)

        self._sb_emax = QDoubleSpinBox()
        self._sb_emax.setRange(-1e6, 1e6)
        self._sb_emax.setDecimals(3)
        self._sb_emax.setValue(100.0)
        model_form.addRow("Emax / Imax:", self._sb_emax)

        self._sb_ec50 = QDoubleSpinBox()
        self._sb_ec50.setRange(1e-9, 1e9)
        self._sb_ec50.setDecimals(4)
        self._sb_ec50.setValue(1.0)
        model_form.addRow("EC50 / IC50:", self._sb_ec50)

        self._sb_n = QDoubleSpinBox()
        self._sb_n.setRange(0.01, 10.0)
        self._sb_n.setDecimals(3)
        self._sb_n.setValue(1.0)
        model_form.addRow("n (coef. Hill):", self._sb_n)

        form_layout.addWidget(model_group)

        coupling_group = QGroupBox("Modo de Concentración")
        coupling_layout = QVBoxLayout(coupling_group)
        self._chk_couple_pk = QCheckBox("Acoplar con Farmacocinética de la pestaña anterior")
        self._chk_couple_pk.toggled.connect(self._on_couple_toggled)
        coupling_layout.addWidget(self._chk_couple_pk)

        self._manual_form_widget = QWidget()
        manual_form = QFormLayout(self._manual_form_widget)
        self._sb_cmin = QDoubleSpinBox()
        self._sb_cmin.setRange(1e-9, 1e9)
        self._sb_cmin.setDecimals(6)
        self._sb_cmin.setValue(0.001)
        manual_form.addRow("Conc. mínima:", self._sb_cmin)

        self._sb_cmax = QDoubleSpinBox()
        self._sb_cmax.setRange(1e-9, 1e9)
        self._sb_cmax.setDecimals(3)
        self._sb_cmax.setValue(100.0)
        manual_form.addRow("Conc. máxima:", self._sb_cmax)
        coupling_layout.addWidget(self._manual_form_widget)
        form_layout.addWidget(coupling_group)

        self._btn_simulate = QPushButton("Simular")
        self._btn_simulate.setObjectName("btnFit")
        self._btn_simulate.clicked.connect(self._on_simulate)
        form_layout.addWidget(self._btn_simulate)

        results_group = QGroupBox("Resultados")
        results_form = QFormLayout(results_group)
        self._lbl_emax_used = QLabel("N/A")
        self._lbl_ec50_used = QLabel("N/A")
        self._lbl_pd2 = QLabel("N/A")
        results_form.addRow("Emax/Imax usado:", self._lbl_emax_used)
        results_form.addRow("EC50/IC50 usado:", self._lbl_ec50_used)
        results_form.addRow("pD2 (-log10 EC50):", self._lbl_pd2)
        form_layout.addWidget(results_group)

        form_layout.addStretch()
        main_layout.addWidget(form_container)

        right_layout = QVBoxLayout()
        self._fig, self._canvas, self._toolbar = _new_canvas()
        self._ax = self._fig.add_subplot(111)
        _style_axes(self._fig, self._ax)
        self._fig.subplots_adjust(left=0.12, right=0.96, top=0.92, bottom=0.12)
        right_layout.addWidget(self._toolbar)
        right_layout.addWidget(self._canvas)
        main_layout.addLayout(right_layout)

    def _on_model_changed(self, model: str) -> None:
        is_hill = model.startswith("Hill")
        self._sb_n.setEnabled(is_hill)

    def _on_couple_toggled(self, checked: bool) -> None:
        self._sb_cmin.setEnabled(not checked)
        self._sb_cmax.setEnabled(not checked)
        self._manual_form_widget.setVisible(not checked)

    def _on_simulate(self) -> None:
        model = self._model_combo.currentText()
        emax = self._sb_emax.value()
        ec50 = self._sb_ec50.value()
        n = self._sb_n.value()

        def pd_func(c: np.ndarray) -> np.ndarray:
            if model == "Emax":
                return pk.pd_emax(c, emax, ec50)
            elif model.startswith("Hill"):
                return pk.pd_hill(c, emax, ec50, n)
            else:
                return pk.pd_fractional_inhibition(c, emax, ec50)

        self._ax.clear()

        if self._chk_couple_pk.isChecked():
            if self._pk_subtab.last_t is None:
                QMessageBox.information(
                    self, "Sin simulación PK",
                    "Primero simula una curva en la pestaña de Farmacocinética."
                )
                return
            t = self._pk_subtab.last_t
            c = self._pk_subtab.last_c
            e = pd_func(c)
            self._ax.plot(t, e, color="#a6e3a1", linewidth=2)
            self._ax.set_xlabel("Tiempo (h)")
            self._ax.set_ylabel("Efecto")
            self._ax.set_title("Efecto vs. Tiempo (acoplado a PK)")
        else:
            cmin = self._sb_cmin.value()
            cmax_v = self._sb_cmax.value()
            c = np.logspace(np.log10(cmin), np.log10(cmax_v), 300)
            e = pd_func(c)
            self._ax.plot(np.log10(c), e, color="#a6e3a1", linewidth=2)
            self._ax.set_xlabel("log[Concentración]")
            self._ax.set_ylabel("Efecto")
            self._ax.set_title("Efecto vs. log[Concentración]")

        _style_axes(self._fig, self._ax)
        self._canvas.draw()

        self._lbl_emax_used.setText(_fmt(emax))
        self._lbl_ec50_used.setText(_fmt(ec50))
        self._lbl_pd2.setText(_fmt(pk.pD2(ec50)) if ec50 > 0 else "N/A")


# ---------------------------------------------------------------------------
# Sub-pestaña C: Órgano Aislado (Schild Plot)
# ---------------------------------------------------------------------------

class _SchildSubTab(QWidget):
    """Sub-pestaña de análisis de órgano aislado / regresión de Schild."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        title = QLabel("Órgano Aislado — Análisis de Schild")
        title.setObjectName("labelTitle")
        main_layout.addWidget(title)

        top_layout = QHBoxLayout()

        # ── Parámetros del agonista ──────────────────────────────────
        agonist_group = QGroupBox("Agonista (curva control)")
        agonist_form = QFormLayout(agonist_group)

        self._sb_ec50 = QDoubleSpinBox()
        self._sb_ec50.setRange(1e-12, 1e6)
        self._sb_ec50.setDecimals(9)
        self._sb_ec50.setValue(1e-7)
        agonist_form.addRow("EC50 agonista (M):", self._sb_ec50)

        self._sb_emax = QDoubleSpinBox()
        self._sb_emax.setRange(0.0, 1e6)
        self._sb_emax.setDecimals(3)
        self._sb_emax.setValue(100.0)
        agonist_form.addRow("Emax:", self._sb_emax)

        self._sb_n = QDoubleSpinBox()
        self._sb_n.setRange(0.01, 10.0)
        self._sb_n.setDecimals(3)
        self._sb_n.setValue(1.0)
        agonist_form.addRow("n (Hill):", self._sb_n)

        self._sb_kb = QDoubleSpinBox()
        self._sb_kb.setRange(1e-12, 1e6)
        self._sb_kb.setDecimals(9)
        self._sb_kb.setValue(1e-7)
        self._sb_kb.setToolTip(
            "KB 'verdadera' usada para generar las razones de dosis simuladas "
            "(propósito didáctico: el Schild plot debe recuperar este valor)."
        )
        agonist_form.addRow("KB antagonista (M):", self._sb_kb)

        top_layout.addWidget(agonist_group)

        # ── Tabla de concentraciones de antagonista ──────────────────
        table_group = QGroupBox("Concentraciones de Antagonista")
        table_layout = QVBoxLayout(table_group)

        self._table = QTableWidget(4, 1)
        self._table.setHorizontalHeaderLabels(["[Antagonista] (M)"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setItem(0, 0, QTableWidgetItem("0"))
        self._table.setItem(1, 0, QTableWidgetItem("1e-8"))
        self._table.setItem(2, 0, QTableWidgetItem("1e-7"))
        self._table.setItem(3, 0, QTableWidgetItem("1e-6"))
        table_layout.addWidget(self._table)

        row_btns = QHBoxLayout()
        btn_add_row = QPushButton("+ Fila")
        btn_add_row.clicked.connect(self._add_row)
        btn_remove_row = QPushButton("− Fila")
        btn_remove_row.clicked.connect(self._remove_row)
        row_btns.addWidget(btn_add_row)
        row_btns.addWidget(btn_remove_row)
        row_btns.addStretch()
        table_layout.addLayout(row_btns)

        top_layout.addWidget(table_group)

        results_group = QGroupBox("Resultados de Schild")
        results_form = QFormLayout(results_group)
        self._lbl_slope = QLabel("N/A")
        self._lbl_pa2 = QLabel("N/A")
        self._lbl_kb_recovered = QLabel("N/A")
        self._lbl_r = QLabel("N/A")
        self._lbl_pd2 = QLabel("N/A")
        results_form.addRow("Pendiente:", self._lbl_slope)
        results_form.addRow("pA2:", self._lbl_pa2)
        results_form.addRow("KB recuperada:", self._lbl_kb_recovered)
        results_form.addRow("r (correlación):", self._lbl_r)
        results_form.addRow("pD2 agonista solo:", self._lbl_pd2)
        top_layout.addWidget(results_group)

        main_layout.addLayout(top_layout)

        self._btn_simulate = QPushButton("Simular y Graficar")
        self._btn_simulate.setObjectName("btnFit")
        self._btn_simulate.clicked.connect(self._on_simulate)
        main_layout.addWidget(self._btn_simulate)

        self._fig, self._canvas, self._toolbar = _new_canvas(figsize=(10, 5))
        self._ax_curves = self._fig.add_subplot(121)
        self._ax_schild = self._fig.add_subplot(122)
        _style_axes(self._fig, self._ax_curves, self._ax_schild)
        self._fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.12, wspace=0.3)
        main_layout.addWidget(self._toolbar)
        main_layout.addWidget(self._canvas)

    def _add_row(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem("0"))

    def _remove_row(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def _read_antagonist_concentrations(self) -> np.ndarray:
        values = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is None or not item.text().strip():
                continue
            try:
                values.append(float(item.text()))
            except ValueError:
                continue
        return np.array(values, dtype=float)

    def _on_simulate(self) -> None:
        ec50 = self._sb_ec50.value()
        emax = self._sb_emax.value()
        n = self._sb_n.value()
        kb = self._sb_kb.value()
        b_concs = self._read_antagonist_concentrations()

        if len(b_concs) < 2:
            QMessageBox.warning(
                self, "Datos insuficientes",
                "Se necesitan al menos 2 concentraciones de antagonista "
                "(incluyendo el control 0) para la regresión de Schild."
            )
            return

        a_concs = np.logspace(np.log10(ec50 / 1000.0), np.log10(ec50 * 1000.0), 300)
        curves, dose_ratios = pk.simulate_schild(a_concs, ec50, n, emax, b_concs, kb)

        try:
            schild_result = pk.schild_regression(b_concs, dose_ratios)
        except Exception as e:
            QMessageBox.critical(self, "Error en regresión de Schild", str(e))
            return

        self._plot_curves(a_concs, curves, b_concs)
        self._plot_schild(b_concs, dose_ratios, schild_result)

        self._lbl_slope.setText(_fmt(schild_result.slope))
        self._lbl_pa2.setText(_fmt(schild_result.pA2))
        self._lbl_kb_recovered.setText(_fmt(schild_result.KB))
        self._lbl_r.setText(_fmt(schild_result.r_value))
        self._lbl_pd2.setText(_fmt(pk.pD2(ec50)))

    def _plot_curves(self, a_concs: np.ndarray, curves, b_concs: np.ndarray) -> None:
        self._ax_curves.clear()
        colors = ["#89b4fa", "#a6e3a1", "#fab387", "#f38ba8",
                  "#cba6f7", "#f9e2af", "#94e2d5", "#89dceb"]
        for i, (curve, b_conc) in enumerate(zip(curves, b_concs)):
            label = f"[B]=0 (control)" if b_conc <= 0 else f"[B]={b_conc:.2e} M"
            self._ax_curves.plot(np.log10(a_concs), curve,
                                  color=colors[i % len(colors)], linewidth=2, label=label)
        self._ax_curves.set_xlabel("log[Agonista]")
        self._ax_curves.set_ylabel("Efecto")
        self._ax_curves.set_title("Curvas Agonista ± Antagonista")
        leg = self._ax_curves.legend(facecolor="#313244", edgecolor="#45475a",
                                      labelcolor="#cdd6f4", fontsize=8)
        leg.get_frame().set_linewidth(0.5)

    def _plot_schild(self, b_concs: np.ndarray, dose_ratios: np.ndarray,
                      result: pk.SchildResult) -> None:
        self._ax_schild.clear()
        mask = (b_concs > 0) & (dose_ratios > 1.0)
        log_b = np.log10(b_concs[mask])
        log_dr = np.log10(dose_ratios[mask] - 1.0)

        self._ax_schild.scatter(log_b, log_dr, color="#89b4fa", s=60, zorder=5)

        if len(log_b) > 0:
            x_line = np.linspace(np.min(log_b) - 0.5, np.max(log_b) + 0.5, 100)
            y_line = result.slope * x_line + result.intercept
            self._ax_schild.plot(x_line, y_line, color="#f38ba8", linewidth=2,
                                  linestyle="--", label="Ajuste lineal")

        self._ax_schild.set_xlabel("log[Antagonista]")
        self._ax_schild.set_ylabel("log(DR-1)")
        self._ax_schild.set_title("Schild Plot")

        text = (f"Pendiente={result.slope:.3f}\n"
                f"pA2={result.pA2:.3f}\n"
                f"KB={result.KB:.3e} M")
        self._ax_schild.text(
            0.05, 0.95, text, transform=self._ax_schild.transAxes,
            fontsize=9, verticalalignment="top", color="#cdd6f4",
            bbox=dict(boxstyle="round", facecolor="#313244", edgecolor="#45475a", alpha=0.85),
        )

        _style_axes(self._fig, self._ax_curves, self._ax_schild)
        self._canvas.draw()


# ---------------------------------------------------------------------------
# Panel principal PK/PD
# ---------------------------------------------------------------------------

class PKPDPanel(QTabWidget):
    """Panel de Farmacocinética / Farmacodinamia con 3 sub-pestañas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pk_tab = _PKSubTab()
        self._pd_tab = _PDSubTab(self._pk_tab)
        self._schild_tab = _SchildSubTab()

        self.addTab(self._pk_tab, "Farmacocinética")
        self.addTab(self._pd_tab, "Farmacodinamia")
        self.addTab(self._schild_tab, "Órgano Aislado (Schild Plot)")
