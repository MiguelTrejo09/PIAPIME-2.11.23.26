"""Panel de configuración del modelo y ajuste."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QCheckBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QFrame, QSizePolicy,
)

from piapime.models.fitting import MODEL_NAME_MAP


_MODELS = list(MODEL_NAME_MAP.keys())

_PARAM_DEFAULTS: dict[str, dict[str, float]] = {
    "4PL (4-Parámetros Logístico)": {
        "Bottom": 0.0, "Top": 100.0, "LogEC50": 0.0, "HillSlope": 1.0
    },
    "3PL (3-Parámetros Logístico)": {
        "Top": 100.0, "LogEC50": 0.0, "HillSlope": 1.0
    },
    "2PL (2-Parámetros Logístico)": {
        "LogEC50": 0.0, "HillSlope": 1.0
    },
    "Ecuación de Hill": {
        "Bottom": 0.0, "Top": 100.0, "LogEC50": 0.0, "HillSlope": 1.0
    },
}


class ModelConfigPanel(QWidget):
    """Panel de configuración del modelo de ajuste."""

    fit_requested = Signal(str, bool, int)   # model_name, bootstrap, n_iter
    fit_all_requested = Signal(str, bool, int)  # model_name, bootstrap, n_iter

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._param_spinboxes: dict[str, QDoubleSpinBox] = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(12)

        # ── Selección de modelo ────────────────────────────────────
        model_group = QGroupBox("Modelo")
        model_group.setMaximumWidth(300)
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(6)

        self._model_combo = QComboBox()
        self._model_combo.addItems(_MODELS)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(QLabel("Tipo de modelo:"))
        model_layout.addWidget(self._model_combo)

        main_layout.addWidget(model_group)

        # ── Parámetros iniciales ───────────────────────────────────
        self._params_group = QGroupBox("Parámetros Iniciales")
        self._params_layout = QFormLayout(self._params_group)
        self._params_layout.setSpacing(4)
        self._params_group.setMinimumWidth(280)
        main_layout.addWidget(self._params_group)

        self._chk_auto_params = QCheckBox("Estimación automática")
        self._chk_auto_params.setChecked(True)
        self._chk_auto_params.toggled.connect(self._toggle_params_visibility)
        self._params_layout.addRow(self._chk_auto_params)

        self._params_container = QWidget()
        self._params_form = QFormLayout(self._params_container)
        self._params_form.setSpacing(4)
        self._params_layout.addRow(self._params_container)
        self._params_container.setVisible(False)

        self._build_param_spinboxes("4PL (4-Parámetros Logístico)")

        # ── Opciones de ajuste ─────────────────────────────────────
        opts_group = QGroupBox("Opciones")
        opts_group.setMaximumWidth(260)
        opts_layout = QVBoxLayout(opts_group)
        opts_layout.setSpacing(6)

        self._chk_bootstrap = QCheckBox("IC Bootstrap (95%)")
        self._chk_bootstrap.setChecked(True)
        self._chk_bootstrap.setToolTip("Calcula intervalos de confianza por bootstrap residual")
        opts_layout.addWidget(self._chk_bootstrap)

        boot_row = QHBoxLayout()
        boot_row.addWidget(QLabel("Iteraciones:"))
        self._spin_boot = QSpinBox()
        self._spin_boot.setRange(100, 5000)
        self._spin_boot.setValue(500)
        self._spin_boot.setSingleStep(100)
        self._spin_boot.setToolTip("Número de iteraciones bootstrap (más iteraciones = más tiempo)")
        boot_row.addWidget(self._spin_boot)
        opts_layout.addLayout(boot_row)

        main_layout.addWidget(opts_group)

        # ── Botones de ajuste ──────────────────────────────────────
        btn_group = QGroupBox("Ajuste")
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.setSpacing(8)

        self._btn_fit = QPushButton("Ajustar Curva")
        self._btn_fit.setObjectName("btnFit")
        self._btn_fit.setToolTip("Ajusta el modelo al dataset activo (Ctrl+R)")
        self._btn_fit.clicked.connect(self._on_fit_clicked)
        btn_layout.addWidget(self._btn_fit)

        self._btn_fit_all = QPushButton("Ajustar Todos")
        self._btn_fit_all.setObjectName("btnFitAll")
        self._btn_fit_all.setToolTip("Ajusta el mismo modelo a todos los datasets")
        self._btn_fit_all.clicked.connect(self._on_fit_all_clicked)
        btn_layout.addWidget(self._btn_fit_all)

        main_layout.addWidget(btn_group)
        main_layout.addStretch()

    # ------------------------------------------------------------------
    # Construcción dinámica de spinboxes
    # ------------------------------------------------------------------

    def _build_param_spinboxes(self, model_name: str) -> None:
        # Limpiar spinboxes anteriores
        while self._params_form.rowCount() > 0:
            self._params_form.removeRow(0)
        self._param_spinboxes.clear()

        defaults = _PARAM_DEFAULTS.get(model_name, {})
        for pname, default_val in defaults.items():
            sb = QDoubleSpinBox()
            sb.setRange(-1e6, 1e6)
            sb.setDecimals(4)
            sb.setSingleStep(0.1)
            sb.setValue(default_val)
            sb.setToolTip(f"Valor inicial para {pname}")
            self._param_spinboxes[pname] = sb
            self._params_form.addRow(f"{pname}:", sb)

    def _toggle_params_visibility(self, auto: bool) -> None:
        self._params_container.setVisible(not auto)

    # ------------------------------------------------------------------
    # Señales
    # ------------------------------------------------------------------

    def _on_model_changed(self, model_name: str) -> None:
        self._build_param_spinboxes(model_name)

    def _on_fit_clicked(self) -> None:
        model = self._model_combo.currentText()
        bootstrap = self._chk_bootstrap.isChecked()
        n_iter = self._spin_boot.value()
        self.fit_requested.emit(model, bootstrap, n_iter)

    def _on_fit_all_clicked(self) -> None:
        model = self._model_combo.currentText()
        bootstrap = self._chk_bootstrap.isChecked()
        n_iter = self._spin_boot.value()
        self.fit_all_requested.emit(model, bootstrap, n_iter)

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    def get_model_name(self) -> str:
        return self._model_combo.currentText()

    def get_initial_params(self) -> list[float] | None:
        if self._chk_auto_params.isChecked():
            return None
        return [sb.value() for sb in self._param_spinboxes.values()]

    def get_bootstrap(self) -> bool:
        return self._chk_bootstrap.isChecked()

    def get_n_bootstrap(self) -> int:
        return self._spin_boot.value()

    def set_fitting_state(self, fitting: bool) -> None:
        self._btn_fit.setEnabled(not fitting)
        self._btn_fit_all.setEnabled(not fitting)
        if fitting:
            self._btn_fit.setText("Ajustando...")
        else:
            self._btn_fit.setText("Ajustar Curva")
