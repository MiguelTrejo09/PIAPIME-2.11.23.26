"""Ventana principal de PIAPIME - Analizador de Curvas Dosis-Respuesta."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QKeySequence, QShortcut, QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QDockWidget, QStatusBar, QLabel, QPushButton,
    QFileDialog, QMessageBox, QToolBar, QInputDialog, QApplication,
)

from piapime.models.fitting import DoseResponseFitter, FittingResult
from piapime.ui.data_panel import DataPanel
from piapime.ui.plot_panel import PlotPanel
from piapime.ui.results_panel import ResultsPanel
from piapime.ui.model_config_panel import ModelConfigPanel
from piapime.ui.pkpd_panel import PKPDPanel
from piapime.ui.admet_panel import ADMETPanel
from piapime.ui.style import DARK_STYLESHEET, LIGHT_STYLESHEET
from piapime.utils.io_utils import export_results_csv, export_results_excel


# ---------------------------------------------------------------------------
# Worker de ajuste (hilo separado)
# ---------------------------------------------------------------------------

class _FitWorker(QObject):
    """Ejecuta el ajuste en un QThread para no bloquear la UI."""

    finished = Signal(str, object)  # (dataset_name, FittingResult)
    error = Signal(str, str)        # (dataset_name, error_message)

    def __init__(self, fitter: DoseResponseFitter, dataset_name: str,
                 x: np.ndarray, y: np.ndarray,
                 model_name: str, initial_params,
                 do_bootstrap: bool, n_bootstrap: int) -> None:
        super().__init__()
        self._fitter = fitter
        self._dataset_name = dataset_name
        self._x = x
        self._y = y
        self._model_name = model_name
        self._initial_params = initial_params
        self._do_bootstrap = do_bootstrap
        self._n_bootstrap = n_bootstrap

    def run(self) -> None:
        try:
            result = self._fitter.fit(
                self._x, self._y,
                model_name=self._model_name,
                initial_params=self._initial_params,
                do_bootstrap=self._do_bootstrap,
                n_bootstrap=self._n_bootstrap,
            )
            self.finished.emit(self._dataset_name, result)
        except Exception as e:
            self.error.emit(self._dataset_name, str(e))


# ---------------------------------------------------------------------------
# Dataset manager (panel lateral)
# ---------------------------------------------------------------------------

class _DatasetManagerWidget(QWidget):
    """Panel lateral para gestionar múltiples datasets."""

    dataset_selected = Signal(str)
    dataset_added = Signal(str)
    dataset_removed = Signal(str)
    dataset_renamed = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._datasets: list[str] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title = QLabel("Datasets")
        title.setObjectName("labelTitle")
        layout.addWidget(title)

        from PySide6.QtWidgets import QListWidget
        self._list = QListWidget()
        self._list.currentTextChanged.connect(self.dataset_selected)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+")
        btn_add.setToolTip("Agregar nuevo dataset")
        btn_add.setMaximumWidth(36)
        btn_add.clicked.connect(self._add_dataset)

        btn_remove = QPushButton("−")
        btn_remove.setToolTip("Eliminar dataset seleccionado")
        btn_remove.setMaximumWidth(36)
        btn_remove.clicked.connect(self._remove_dataset)

        btn_rename = QPushButton("✎")
        btn_rename.setToolTip("Renombrar dataset")
        btn_rename.setMaximumWidth(36)
        btn_rename.clicked.connect(self._rename_dataset)

        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_rename)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Agregar dataset por defecto
        self._add_named_dataset("Dataset 1")

    def _add_dataset(self) -> None:
        n = len(self._datasets) + 1
        name = f"Dataset {n}"
        self._add_named_dataset(name)

    def _add_named_dataset(self, name: str) -> None:
        if name in self._datasets:
            return
        self._datasets.append(name)
        self._list.addItem(name)
        self._list.setCurrentRow(self._list.count() - 1)
        self.dataset_added.emit(name)

    def _remove_dataset(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        name = item.text()
        if len(self._datasets) == 1:
            QMessageBox.warning(self, "Eliminar", "Debe haber al menos un dataset.")
            return
        reply = QMessageBox.question(
            self, "Eliminar dataset",
            f"¿Eliminar '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            row = self._list.row(item)
            self._list.takeItem(row)
            self._datasets.remove(name)
            self.dataset_removed.emit(name)

    def _rename_dataset(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, "Renombrar dataset",
            "Nuevo nombre:", text=old_name
        )
        if ok and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            item.setText(new_name)
            idx = self._datasets.index(old_name)
            self._datasets[idx] = new_name
            self.dataset_renamed.emit(old_name, new_name)

    def current_dataset(self) -> str | None:
        item = self._list.currentItem()
        return item.text() if item else None

    def all_datasets(self) -> list[str]:
        return list(self._datasets)

    def add_dataset(self, name: str) -> None:
        self._add_named_dataset(name)


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Ventana principal de PIAPIME."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PIAPIME — Analizador de Curvas Dosis-Respuesta")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 800)

        self._fitter = DoseResponseFitter()
        self._fit_threads: dict[str, QThread] = {}
        self._fit_results: dict[str, FittingResult] = {}

        # {dataset_name: {"x": array, "y": array}}
        self._dataset_data: dict[str, dict] = {}

        self._dark_mode = True
        self._dataset_dock_was_visible = True
        self._model_dock_was_visible = True
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        # ── Panel lateral de datasets ──────────────────────────────
        self._dataset_manager = _DatasetManagerWidget()
        self._dataset_dock = QDockWidget("Datasets", self)
        self._dataset_dock.setWidget(self._dataset_manager)
        self._dataset_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self._dataset_dock.setMinimumWidth(160)
        self._dataset_dock.setMaximumWidth(250)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._dataset_dock)

        # ── Contenido del analizador dosis-respuesta: splitter horizontal ──
        dose_response_widget = QWidget()
        main_layout = QVBoxLayout(dose_response_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Panel izquierdo: datos + resultados
        left_tabs = QTabWidget()
        left_tabs.setMinimumWidth(320)

        self._data_panel = DataPanel()
        left_tabs.addTab(self._data_panel, "Datos")

        self._results_panel = ResultsPanel()
        left_tabs.addTab(self._results_panel, "Resultados")

        splitter.addWidget(left_tabs)

        # Panel derecho: gráfica
        self._plot_panel = PlotPanel()
        splitter.addWidget(self._plot_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([420, 680])

        # ── Dock inferior: configuración del modelo ─────────────────
        self._model_config = ModelConfigPanel()
        self._model_dock = QDockWidget("Configuración del Modelo", self)
        self._model_dock.setWidget(self._model_config)
        self._model_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self._model_dock.setMaximumHeight(180)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._model_dock)

        # ── Pestañas de nivel superior ───────────────────────────────
        self._main_tabs = QTabWidget()
        self.setCentralWidget(self._main_tabs)

        self._main_tabs.addTab(dose_response_widget, "Curvas Dosis-Respuesta")

        self._pkpd_panel = PKPDPanel()
        self._main_tabs.addTab(self._pkpd_panel, "Farmacocinética / Farmacodinamia")

        self._admet_panel = ADMETPanel()
        self._main_tabs.addTab(self._admet_panel, "ADMET")

        self._main_tabs.currentChanged.connect(self._on_main_tab_changed)

        # ── Status bar ──────────────────────────────────────────────
        self._status_label = QLabel("Listo")
        self.statusBar().addWidget(self._status_label)
        self._progress_label = QLabel("")
        self.statusBar().addPermanentWidget(self._progress_label)

    # ------------------------------------------------------------------
    # Cambio de pestaña principal: visibilidad de docks
    # ------------------------------------------------------------------

    def _on_main_tab_changed(self, index: int) -> None:
        if index == 0:
            self._dataset_dock.setVisible(self._dataset_dock_was_visible)
            self._model_dock.setVisible(self._model_dock_was_visible)
        else:
            self._dataset_dock_was_visible = self._dataset_dock.isVisible()
            self._model_dock_was_visible = self._model_dock.isVisible()
            self._dataset_dock.setVisible(False)
            self._model_dock.setVisible(False)

    # ------------------------------------------------------------------
    # Menús
    # ------------------------------------------------------------------

    def _setup_menus(self) -> None:
        mb = self.menuBar()

        # ── Archivo ────────────────────────────────────────────────
        file_menu = mb.addMenu("Archivo")

        act_new = QAction("Nuevo Proyecto", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._new_project)
        file_menu.addAction(act_new)

        file_menu.addSeparator()

        act_open_csv = QAction("Importar CSV...", self)
        act_open_csv.setShortcut("Ctrl+O")
        act_open_csv.triggered.connect(self._data_panel._import_csv)
        file_menu.addAction(act_open_csv)

        act_open_excel = QAction("Importar Excel...", self)
        act_open_excel.triggered.connect(self._data_panel._import_excel)
        file_menu.addAction(act_open_excel)

        file_menu.addSeparator()

        act_export_csv = QAction("Exportar Resultados (CSV)...", self)
        act_export_csv.triggered.connect(self._export_results_csv)
        file_menu.addAction(act_export_csv)

        act_export_excel = QAction("Exportar Resultados (Excel)...", self)
        act_export_excel.triggered.connect(self._export_results_excel)
        file_menu.addAction(act_export_excel)

        act_export_plot = QAction("Exportar Figura...", self)
        act_export_plot.setShortcut("Ctrl+Shift+S")
        act_export_plot.triggered.connect(self._plot_panel._export_figure)
        file_menu.addAction(act_export_plot)

        file_menu.addSeparator()

        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # ── Análisis ───────────────────────────────────────────────
        analysis_menu = mb.addMenu("Análisis")

        act_fit = QAction("Ajustar Curva", self)
        act_fit.setShortcut("Ctrl+R")
        act_fit.triggered.connect(self._on_fit_requested_from_menu)
        analysis_menu.addAction(act_fit)

        act_fit_all = QAction("Ajustar Todos los Datasets", self)
        act_fit_all.setShortcut("Ctrl+Shift+R")
        act_fit_all.triggered.connect(self._on_fit_all_requested_from_menu)
        analysis_menu.addAction(act_fit_all)

        analysis_menu.addSeparator()

        act_clear_fit = QAction("Limpiar Ajuste Actual", self)
        act_clear_fit.triggered.connect(self._clear_current_fit)
        analysis_menu.addAction(act_clear_fit)

        act_clear_all = QAction("Limpiar Todos los Ajustes", self)
        act_clear_all.triggered.connect(self._clear_all_fits)
        analysis_menu.addAction(act_clear_all)

        # ── Ver ────────────────────────────────────────────────────
        view_menu = mb.addMenu("Ver")

        act_theme = QAction("Cambiar Tema (Oscuro/Claro)", self)
        act_theme.setShortcut("Ctrl+T")
        act_theme.triggered.connect(self._toggle_theme)
        view_menu.addAction(act_theme)

        # ── Ayuda ──────────────────────────────────────────────────
        help_menu = mb.addMenu("Ayuda")

        act_about = QAction("Acerca de PIAPIME...", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

        act_models = QAction("Descripción de Modelos...", self)
        act_models.triggered.connect(self._show_models_info)
        help_menu.addAction(act_models)

        act_pkpd = QAction("Fórmulas Farmacocinéticas...", self)
        act_pkpd.triggered.connect(self._show_pkpd_info)
        help_menu.addAction(act_pkpd)

    # ------------------------------------------------------------------
    # Barra de herramientas
    # ------------------------------------------------------------------

    def _setup_toolbar(self) -> None:
        tb = QToolBar("Principal")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        act_new = QAction("Nuevo", self)
        act_new.setToolTip("Nuevo proyecto")
        act_new.triggered.connect(self._new_project)
        tb.addAction(act_new)

        tb.addSeparator()

        act_import = QAction("Importar CSV", self)
        act_import.setToolTip("Importar datos desde CSV")
        act_import.triggered.connect(self._data_panel._import_csv)
        tb.addAction(act_import)

        tb.addSeparator()

        act_fit_tb = QAction("▶ Ajustar Curva", self)
        act_fit_tb.setToolTip("Ajustar modelo (Ctrl+R)")
        act_fit_tb.triggered.connect(self._on_fit_requested_from_menu)
        tb.addAction(act_fit_tb)

        tb.addSeparator()

        act_theme_tb = QAction("☀ Tema", self)
        act_theme_tb.setToolTip("Cambiar entre tema oscuro y claro")
        act_theme_tb.triggered.connect(self._toggle_theme)
        tb.addAction(act_theme_tb)

    # ------------------------------------------------------------------
    # Conexión de señales
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        # Dataset manager
        self._dataset_manager.dataset_selected.connect(self._on_dataset_selected)
        self._dataset_manager.dataset_added.connect(self._on_dataset_added)
        self._dataset_manager.dataset_removed.connect(self._on_dataset_removed)
        self._dataset_manager.dataset_renamed.connect(self._on_dataset_renamed)

        # Data panel
        self._data_panel.data_changed.connect(self._on_data_changed)

        # Model config
        self._model_config.fit_requested.connect(self._on_fit_requested)
        self._model_config.fit_all_requested.connect(self._on_fit_all_requested)

        # Shortcut Ctrl+R
        sc = QShortcut(QKeySequence("Ctrl+R"), self)
        sc.activated.connect(self._on_fit_requested_from_menu)

    # ------------------------------------------------------------------
    # Manejo de datasets
    # ------------------------------------------------------------------

    def _on_dataset_added(self, name: str) -> None:
        self._dataset_data[name] = {"x": np.array([]), "y": np.array([])}
        color = self._plot_panel.next_color()
        self._plot_panel._datasets.setdefault(name, {})["color"] = color

    def _on_dataset_selected(self, name: str) -> None:
        if not name:
            return
        ds = self._dataset_data.get(name, {})
        x = ds.get("x", np.array([]))
        y = ds.get("y", np.array([]))
        if len(x) > 0:
            self._data_panel.set_data(x, y)
        else:
            self._data_panel._load_defaults()

    def _on_dataset_removed(self, name: str) -> None:
        self._dataset_data.pop(name, None)
        self._fit_results.pop(name, None)
        self._plot_panel.clear_dataset(name)
        self._results_panel.remove_result(name)

    def _on_dataset_renamed(self, old: str, new: str) -> None:
        if old in self._dataset_data:
            self._dataset_data[new] = self._dataset_data.pop(old)
        if old in self._fit_results:
            self._fit_results[new] = self._fit_results.pop(old)
        if old in self._plot_panel._datasets:
            self._plot_panel._datasets[new] = self._plot_panel._datasets.pop(old)
        self._plot_panel.refresh_plot()

    def _on_data_changed(self, x: np.ndarray, y: np.ndarray) -> None:
        name = self._dataset_manager.current_dataset()
        if not name:
            return
        self._dataset_data[name] = {"x": x, "y": y}
        color = self._plot_panel.get_color(name)
        self._plot_panel.plot_data(name, x, y, color)

    # ------------------------------------------------------------------
    # Ajuste de curvas
    # ------------------------------------------------------------------

    def _on_fit_requested_from_menu(self) -> None:
        model = self._model_config.get_model_name()
        bootstrap = self._model_config.get_bootstrap()
        n_iter = self._model_config.get_n_bootstrap()
        self._on_fit_requested(model, bootstrap, n_iter)

    def _on_fit_all_requested_from_menu(self) -> None:
        model = self._model_config.get_model_name()
        bootstrap = self._model_config.get_bootstrap()
        n_iter = self._model_config.get_n_bootstrap()
        self._on_fit_all_requested(model, bootstrap, n_iter)

    def _on_fit_requested(self, model: str, bootstrap: bool, n_iter: int) -> None:
        name = self._dataset_manager.current_dataset()
        if not name:
            return
        ds = self._dataset_data.get(name, {})
        x = ds.get("x", np.array([]))
        y = ds.get("y", np.array([]))
        if len(x) < 4:
            QMessageBox.warning(self, "Sin datos",
                                "Necesitas al menos 4 puntos de datos para ajustar.")
            return
        self._run_fit(name, x, y, model, self._model_config.get_initial_params(),
                      bootstrap, n_iter)

    def _on_fit_all_requested(self, model: str, bootstrap: bool, n_iter: int) -> None:
        for name in self._dataset_manager.all_datasets():
            ds = self._dataset_data.get(name, {})
            x = ds.get("x", np.array([]))
            y = ds.get("y", np.array([]))
            if len(x) >= 4:
                self._run_fit(name, x, y, model, None, bootstrap, n_iter)

    def _run_fit(self, name: str, x: np.ndarray, y: np.ndarray,
                 model: str, initial_params, bootstrap: bool, n_iter: int) -> None:
        if name in self._fit_threads and self._fit_threads[name].isRunning():
            return

        self._status_label.setText(f"Ajustando '{name}' con {model}...")
        self._progress_label.setText("⏳ Procesando...")
        self._model_config.set_fitting_state(True)

        worker = _FitWorker(self._fitter, name, x, y, model, initial_params,
                            bootstrap, n_iter)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_fit_finished)
        worker.error.connect(self._on_fit_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup_thread(name))

        self._fit_threads[name] = thread
        self._worker_refs = getattr(self, "_worker_refs", {})
        self._worker_refs[name] = worker

        thread.start()

    def _on_fit_finished(self, name: str, result: FittingResult) -> None:
        self._fit_results[name] = result
        color = self._plot_panel.get_color(name)
        self._plot_panel.plot_fit(name, result)
        self._results_panel.show_result(name, result, color)
        self._status_label.setText(
            f"'{name}': R²={result.r_squared:.4f}  EC50={result.ec50:.4e}"
            if result.success else f"'{name}': ajuste fallido — {result.message}"
        )
        self._progress_label.setText("")
        self._model_config.set_fitting_state(False)

    def _on_fit_error(self, name: str, msg: str) -> None:
        self._status_label.setText(f"Error en '{name}': {msg}")
        self._progress_label.setText("")
        self._model_config.set_fitting_state(False)
        QMessageBox.critical(self, "Error de ajuste", f"Error al ajustar '{name}':\n{msg}")

    def _cleanup_thread(self, name: str) -> None:
        self._fit_threads.pop(name, None)
        if hasattr(self, "_worker_refs"):
            self._worker_refs.pop(name, None)

    # ------------------------------------------------------------------
    # Limpiar ajustes
    # ------------------------------------------------------------------

    def _clear_current_fit(self) -> None:
        name = self._dataset_manager.current_dataset()
        if not name:
            return
        self._fit_results.pop(name, None)
        if name in self._plot_panel._datasets:
            self._plot_panel._datasets[name].pop("fit", None)
        self._plot_panel.refresh_plot()
        self._results_panel.remove_result(name)

    def _clear_all_fits(self) -> None:
        self._fit_results.clear()
        for ds in self._plot_panel._datasets.values():
            ds.pop("fit", None)
        self._plot_panel.refresh_plot()
        self._results_panel.clear_all()

    # ------------------------------------------------------------------
    # Nuevo proyecto
    # ------------------------------------------------------------------

    def _new_project(self) -> None:
        reply = QMessageBox.question(
            self, "Nuevo proyecto",
            "¿Crear nuevo proyecto? Se perderán los datos actuales.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._dataset_data.clear()
            self._fit_results.clear()
            self._plot_panel.clear_all()
            self._results_panel.clear_all()
            self._data_panel._load_defaults()
            self._status_label.setText("Nuevo proyecto creado.")

    # ------------------------------------------------------------------
    # Exportar
    # ------------------------------------------------------------------

    def _export_results_csv(self) -> None:
        if not self._fit_results:
            QMessageBox.information(self, "Sin resultados",
                                    "No hay resultados para exportar. Ajusta un modelo primero.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar resultados", "resultados_dosis_respuesta.csv",
            "CSV (*.csv);;Todos (*.*)"
        )
        if path:
            try:
                export_results_csv(self._fit_results, path)
                QMessageBox.information(self, "Exportar", f"Resultados guardados en:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_results_excel(self) -> None:
        if not self._fit_results:
            QMessageBox.information(self, "Sin resultados",
                                    "No hay resultados para exportar. Ajusta un modelo primero.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar resultados", "resultados_dosis_respuesta.xlsx",
            "Excel (*.xlsx);;Todos (*.*)"
        )
        if path:
            try:
                export_results_excel(self._fit_results, path)
                QMessageBox.information(self, "Exportar", f"Resultados guardados en:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------

    def _toggle_theme(self) -> None:
        self._dark_mode = not self._dark_mode
        QApplication.instance().setStyleSheet(
            DARK_STYLESHEET if self._dark_mode else LIGHT_STYLESHEET
        )

    # ------------------------------------------------------------------
    # Diálogos de información
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "Acerca de PIAPIME",
            "<h2>PIAPIME v2.11.23.26</h2>"
            "<p><b>Analizador de Curvas Dosis-Respuesta</b></p>"
            "<p>Desarrollado para análisis farmacológico y toxicológico.</p>"
            "<p>Soporta modelos 4PL, 3PL, 2PL y Ecuación de Hill con "
            "intervalos de confianza bootstrap.</p>"
            "<p><b>Farmacocinética / Farmacodinamia:</b> simulación de "
            "modelos de 1, 2 y 3 compartimentos, modelos PD (Emax, Hill, "
            "inhibición fraccional) y análisis de órgano aislado con "
            "regresión de Schild (pA2/pD2/KB).</p>"
            "<p><b>ADMET:</b> descriptores fisicoquímicos offline basados "
            "en RDKit (LogP, TPSA, reglas de Lipinski/Veber/Egan), sin "
            "conexión a internet ni modelos de aprendizaje automático.</p>"
            "<p><i>UNAM FESC · Área de Farmacología</i></p>"
        )

    def _show_models_info(self) -> None:
        info = (
            "<h3>Modelos de Curva Dosis-Respuesta</h3>"
            "<p><b>4PL (4-Parámetros Logístico):</b><br>"
            "y = Bottom + (Top − Bottom) / (1 + 10^(HillSlope·(LogEC50 − log₁₀(x))))<br>"
            "Parámetros: Bottom, Top, LogEC50, HillSlope</p>"
            "<p><b>3PL (3-Parámetros Logístico):</b><br>"
            "y = Top / (1 + 10^(HillSlope·(LogEC50 − log₁₀(x))))<br>"
            "Bottom fijo en 0</p>"
            "<p><b>2PL (2-Parámetros Logístico):</b><br>"
            "y = 100 / (1 + 10^(HillSlope·(LogEC50 − log₁₀(x))))<br>"
            "Bottom=0, Top=100 fijos</p>"
            "<p><b>Ecuación de Hill:</b><br>"
            "Equivalente al 4PL con nomenclatura farmacológica.</p>"
            "<hr>"
            "<p><b>EC50:</b> Concentración que produce el 50% del efecto máximo.<br>"
            "<b>IC50:</b> Concentración que inhibe el 50% de la respuesta.<br>"
            "<b>HillSlope:</b> Coeficiente de Hill (pendiente de la curva sigmoidea).</p>"
        )
        QMessageBox.information(self, "Descripción de Modelos", info)

    def _show_pkpd_info(self) -> None:
        info = (
            "<h3>Fórmulas de Farmacocinética / Farmacodinamia</h3>"
            "<p><b>1 compartimento — IV bolo:</b><br>"
            "C(t) = (Dosis/Vd) · e^(−Ke·t)</p>"
            "<p><b>1 compartimento — IV infusión:</b><br>"
            "Durante: C(t) = (R0/(Vd·Ke)) · (1 − e^(−Ke·t))<br>"
            "Después de Tinf: C(t) = C(Tinf) · e^(−Ke·(t−Tinf))</p>"
            "<p><b>1 compartimento — Oral/extravascular:</b><br>"
            "C(t) = (F·Dosis·Ka)/(Vd·(Ka−Ke)) · (e^(−Ke·t) − e^(−Ka·t))<br>"
            "Caso límite Ka=Ke (flip-flop): C(t) = (F·Dosis·Ka/Vd)·t·e^(−Ka·t)</p>"
            "<p><b>Multidosis:</b> superposición de curvas de dosis única "
            "desplazadas por k·tau, para k=0..n−1 (solo t ≥ k·tau).</p>"
            "<p><b>Parámetros derivados:</b><br>"
            "t½ = ln(2)/Ke · Cl = Ke·Vd · AUC = trapezoidal (numérica) o "
            "F·Dosis/Cl (analítica) · Css_avg = F·Dosis/(Cl·tau)</p>"
            "<hr>"
            "<p><b>2 compartimentos (IV bolo):</b><br>"
            "C(t) = A·e^(−alpha·t) + B·e^(−beta·t)<br>"
            "alpha+beta = k10+k12+k21 · alpha·beta = k10·k21<br>"
            "A = (Dosis/Vc)·(alpha−k21)/(alpha−beta) · "
            "B = (Dosis/Vc)·(k21−beta)/(alpha−beta)</p>"
            "<p><b>3 compartimentos (IV bolo):</b><br>"
            "C(t) = A·e^(−alpha·t) + B·e^(−beta·t) + C·e^(−gamma·t)</p>"
            "<hr>"
            "<p><b>Modelos PD:</b><br>"
            "Emax: E = Emax·C/(EC50+C) &nbsp; · &nbsp; "
            "Hill: E = Emax·C^n/(EC50^n+C^n) &nbsp; · &nbsp; "
            "Inhibición: I = Imax·C/(IC50+C)</p>"
            "<p><b>Órgano aislado / Schild:</b><br>"
            "DR = 1 + [B]/KB · curva desplazada: "
            "E = Emax·A^n/((EC50·DR)^n+A^n)<br>"
            "Regresión: log(DR−1) vs log[B] → pendiente, pA2 = −intercepto/pendiente, "
            "KB = 10^(−pA2)<br>"
            "pD2 = −log10(EC50) (potencia del agonista solo)</p>"
        )
        QMessageBox.information(self, "Fórmulas Farmacocinéticas / Farmacodinámicas", info)
