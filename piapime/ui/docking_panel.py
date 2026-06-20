"""Panel de Acoplamiento Molecular (AutoDock Vina).

IMPORTANTE: este panel requiere dependencias externas que pueden no estar
disponibles en todos los entornos:
  - El binario de AutoDock Vina debe estar instalado por el usuario/sistema
    (no se distribuye vía pip de forma universal); se busca en el PATH o en
    una ruta personalizada indicada en este panel.
  - RDKit y meeko (opcionales) se usan solo para generar el ligando en
    formato PDBQT a partir de un SMILES.
  - La visualización 3D usa PySide6 QtWebEngineWidgets (opcional) + py3Dmol
    vía CDN; si QtWebEngine no está instalado, se muestra un mensaje
    explicativo en su lugar (la tabla de poses y el log de Vina siguen
    funcionando sin la vista 3D).

Todas las rutas de error (binario de Vina ausente, meeko ausente, receptor
con formato incorrecto, etc.) se manejan explícitamente y se reportan al
usuario en español mediante QMessageBox, nunca dejando que la aplicación
se bloquee o falle silenciosamente.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QSpinBox, QGroupBox, QScrollArea, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QFileDialog,
    QMessageBox, QSplitter,
)

from piapime.docking.vina_runner import (
    DockingResult, prepare_ligand_from_smiles, run_vina_docking,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _WEBENGINE_AVAILABLE = True
except ImportError:
    _WEBENGINE_AVAILABLE = False


_LIGAND_EXAMPLES = {
    "Aspirina": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "Cafeína": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "Ibuprofeno": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
}


# ---------------------------------------------------------------------------
# Worker de docking (hilo separado, mismo patrón que _FitWorker en main_window.py)
# ---------------------------------------------------------------------------

class _DockingWorker(QObject):
    """Ejecuta `run_vina_docking` en un QThread para no bloquear la UI."""

    finished = Signal(object)  # DockingResult
    error = Signal(str)

    def __init__(self, receptor_pdbqt: str, ligand_pdbqt: str, output_pdbqt: str,
                 center: tuple, box_size: tuple, exhaustiveness: int,
                 num_modes: int, vina_executable: Optional[str]) -> None:
        super().__init__()
        self._receptor = receptor_pdbqt
        self._ligand = ligand_pdbqt
        self._output = output_pdbqt
        self._center = center
        self._box_size = box_size
        self._exhaustiveness = exhaustiveness
        self._num_modes = num_modes
        self._vina_executable = vina_executable

    def run(self) -> None:
        try:
            result = run_vina_docking(
                self._receptor, self._ligand, self._output,
                self._center, self._box_size,
                exhaustiveness=self._exhaustiveness,
                num_modes=self._num_modes,
                vina_executable=self._vina_executable,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DockingPanel(QWidget):
    """Panel de Acoplamiento Molecular (AutoDock Vina)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ligand_pdbqt_path: str = ""
        self._output_pdbqt_path: str = ""
        self._thread: Optional[QThread] = None
        self._worker: Optional[_DockingWorker] = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ── Panel de formulario (izquierda) ─────────────────────────
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_scroll.setMaximumWidth(420)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(8)

        title = QLabel("Acoplamiento Molecular (AutoDock Vina)")
        title.setObjectName("labelTitle")
        form_layout.addWidget(title)

        subtitle = QLabel(
            "Requiere un binario de AutoDock Vina instalado en el sistema y un "
            "receptor ya preparado en formato .pdbqt. Esta funcionalidad no "
            "pudo verificarse de extremo a extremo en este entorno de "
            "desarrollo (sin acceso a Vina/meeko); revisa los mensajes de "
            "error si algo falla."
        )
        subtitle.setObjectName("labelSubtitle")
        subtitle.setWordWrap(True)
        form_layout.addWidget(subtitle)

        # ── Grupo Receptor ───────────────────────────────────────────
        receptor_group = QGroupBox("Receptor")
        receptor_layout = QVBoxLayout(receptor_group)

        receptor_row = QHBoxLayout()
        self._receptor_edit = QLineEdit()
        self._receptor_edit.setReadOnly(True)
        self._receptor_edit.setPlaceholderText("Selecciona un archivo .pdbqt...")
        receptor_row.addWidget(self._receptor_edit)
        btn_receptor = QPushButton("Buscar...")
        btn_receptor.clicked.connect(self._on_browse_receptor)
        receptor_row.addWidget(btn_receptor)
        receptor_layout.addLayout(receptor_row)

        receptor_note = QLabel(
            "El receptor debe estar ya preparado (hidrógenos añadidos, cargas "
            "asignadas, tipado de átomos) usando AutoDockTools, ADFR o Meeko "
            "antes de cargarlo aquí. Este panel no realiza esa conversión."
        )
        receptor_note.setObjectName("labelSubtitle")
        receptor_note.setWordWrap(True)
        receptor_layout.addWidget(receptor_note)

        form_layout.addWidget(receptor_group)

        # ── Grupo Ligando ─────────────────────────────────────────────
        ligand_group = QGroupBox("Ligando")
        ligand_layout = QVBoxLayout(ligand_group)

        smiles_row = QHBoxLayout()
        smiles_row.addWidget(QLabel("SMILES:"))
        self._smiles_edit = QLineEdit()
        self._smiles_edit.setPlaceholderText("Ej. CC(=O)OC1=CC=CC=C1C(=O)O (Aspirina)")
        smiles_row.addWidget(self._smiles_edit)
        ligand_layout.addLayout(smiles_row)

        examples_row = QHBoxLayout()
        examples_row.addWidget(QLabel("Ejemplos:"))
        for name, smiles in _LIGAND_EXAMPLES.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked=False, s=smiles: self._smiles_edit.setText(s))
            examples_row.addWidget(btn)
        examples_row.addStretch()
        ligand_layout.addLayout(examples_row)

        self._btn_prepare_ligand = QPushButton("Generar PDBQT del ligando")
        self._btn_prepare_ligand.clicked.connect(self._on_prepare_ligand)
        ligand_layout.addWidget(self._btn_prepare_ligand)

        self._ligand_status_label = QLabel("Ligando no preparado.")
        self._ligand_status_label.setWordWrap(True)
        ligand_layout.addWidget(self._ligand_status_label)

        form_layout.addWidget(ligand_group)

        # ── Grupo Caja de búsqueda ────────────────────────────────────
        box_group = QGroupBox("Caja de Búsqueda (Search Box)")
        box_form = QFormLayout(box_group)

        self._sb_center_x = self._make_spin(-1000.0, 1000.0, 0.0)
        self._sb_center_y = self._make_spin(-1000.0, 1000.0, 0.0)
        self._sb_center_z = self._make_spin(-1000.0, 1000.0, 0.0)
        box_form.addRow("Centro X (Å):", self._sb_center_x)
        box_form.addRow("Centro Y (Å):", self._sb_center_y)
        box_form.addRow("Centro Z (Å):", self._sb_center_z)

        self._sb_size_x = self._make_spin(1.0, 200.0, 20.0)
        self._sb_size_y = self._make_spin(1.0, 200.0, 20.0)
        self._sb_size_z = self._make_spin(1.0, 200.0, 20.0)
        box_form.addRow("Tamaño X (Å):", self._sb_size_x)
        box_form.addRow("Tamaño Y (Å):", self._sb_size_y)
        box_form.addRow("Tamaño Z (Å):", self._sb_size_z)

        box_note = QLabel(
            "Estas coordenadas definen la caja de búsqueda alrededor del "
            "sitio de unión. Debes determinarlas a partir de la estructura "
            "del receptor (p. ej. centro de un ligando co-cristalizado), ya "
            "que esta versión no incluye un visor 3D interactivo para "
            "seleccionar la caja."
        )
        box_note.setObjectName("labelSubtitle")
        box_note.setWordWrap(True)
        box_form.addRow(box_note)

        form_layout.addWidget(box_group)

        # ── Grupo Parámetros de Vina ──────────────────────────────────
        params_group = QGroupBox("Parámetros de Vina")
        params_form = QFormLayout(params_group)

        self._sb_exhaustiveness = QSpinBox()
        self._sb_exhaustiveness.setRange(1, 32)
        self._sb_exhaustiveness.setValue(8)
        params_form.addRow("Exhaustiveness:", self._sb_exhaustiveness)

        self._sb_num_modes = QSpinBox()
        self._sb_num_modes.setRange(1, 20)
        self._sb_num_modes.setValue(9)
        params_form.addRow("Número de modos:", self._sb_num_modes)

        vina_path_row = QHBoxLayout()
        self._vina_path_edit = QLineEdit()
        self._vina_path_edit.setPlaceholderText("Opcional: ruta completa al ejecutable de Vina")
        vina_path_row.addWidget(self._vina_path_edit)
        btn_vina_path = QPushButton("Buscar...")
        btn_vina_path.clicked.connect(self._on_browse_vina_executable)
        vina_path_row.addWidget(btn_vina_path)
        params_form.addRow("Ruta personalizada a Vina:", vina_path_row)

        form_layout.addWidget(params_group)

        self._btn_run = QPushButton("Ejecutar Docking")
        self._btn_run.setObjectName("btnFit")
        self._btn_run.clicked.connect(self._on_run_docking)
        form_layout.addWidget(self._btn_run)

        form_layout.addStretch()
        form_scroll.setWidget(form_container)
        splitter.addWidget(form_scroll)

        # ── Panel derecho: resultados/visualización ───────────────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(8)

        results_title = QLabel("Resultados del Docking")
        results_title.setObjectName("labelTitle")
        right_layout.addWidget(results_title)

        self._poses_table = QTableWidget(0, 4)
        self._poses_table.setHorizontalHeaderLabels(
            ["Rank", "Afinidad (kcal/mol)", "RMSD l.b.", "RMSD u.b."]
        )
        self._poses_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._poses_table.verticalHeader().setVisible(False)
        self._poses_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._poses_table.setMaximumHeight(220)
        right_layout.addWidget(self._poses_table)

        log_group = QGroupBox("Log de Vina (salida cruda)")
        log_layout = QVBoxLayout(log_group)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(160)
        log_layout.addWidget(self._log_text)
        right_layout.addWidget(log_group)

        viz_group = QGroupBox("Visualización 3D")
        viz_layout = QVBoxLayout(viz_group)
        if _WEBENGINE_AVAILABLE:
            self._web_view = QWebEngineView()
            self._web_view.setMinimumHeight(300)
            viz_layout.addWidget(self._web_view)
            self._viz_fallback_label = None
        else:
            self._web_view = None
            self._viz_fallback_label = QLabel(
                "Visualización 3D no disponible: instala el paquete PySide6 "
                "con soporte de WebEngine (pip install PySide6-Addons o "
                "equivalente) para ver las poses en 3D. Mientras tanto, "
                "revisa la tabla de poses y el archivo de salida indicado "
                "abajo."
            )
            self._viz_fallback_label.setWordWrap(True)
            viz_layout.addWidget(self._viz_fallback_label)

        self._output_path_label = QLabel("Archivo de salida: (ninguno aún)")
        self._output_path_label.setWordWrap(True)
        viz_layout.addWidget(self._output_path_label)

        right_layout.addWidget(viz_group)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    @staticmethod
    def _make_spin(lo: float, hi: float, default: float) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setDecimals(2)
        sb.setValue(default)
        return sb

    # ------------------------------------------------------------------
    # Acciones — Receptor
    # ------------------------------------------------------------------

    def _on_browse_receptor(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar receptor preparado", "", "Archivos PDBQT (*.pdbqt);;Todos (*.*)"
        )
        if path:
            self._receptor_edit.setText(path)

    def _on_browse_vina_executable(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar ejecutable de Vina", "", "Todos los archivos (*.*)"
        )
        if path:
            self._vina_path_edit.setText(path)

    # ------------------------------------------------------------------
    # Acciones — Ligando
    # ------------------------------------------------------------------

    def _on_prepare_ligand(self) -> None:
        smiles = self._smiles_edit.text().strip()
        if not smiles:
            QMessageBox.warning(self, "Sin SMILES",
                                 "Ingresa una cadena SMILES para el ligando.")
            return

        out_name = f"piapime_ligand_{uuid.uuid4().hex[:8]}.pdbqt"
        out_path = str(Path(tempfile.gettempdir()) / out_name)

        ok, msg = prepare_ligand_from_smiles(smiles, out_path)
        if ok:
            self._ligand_pdbqt_path = out_path
            self._ligand_status_label.setText(
                f"Ligando preparado correctamente:\n{out_path}"
            )
            self._ligand_status_label.setStyleSheet("color: #a6e3a1;")
        else:
            self._ligand_pdbqt_path = ""
            self._ligand_status_label.setText(f"Error: {msg}")
            self._ligand_status_label.setStyleSheet("color: #f38ba8;")
            QMessageBox.warning(self, "Error al preparar ligando", msg)

    # ------------------------------------------------------------------
    # Acciones — Docking
    # ------------------------------------------------------------------

    def _on_run_docking(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(self, "Docking en curso",
                                     "Ya hay un docking en ejecución. Espera a que termine.")
            return

        receptor = self._receptor_edit.text().strip()
        if not receptor:
            QMessageBox.warning(self, "Falta receptor",
                                 "Selecciona un archivo de receptor (.pdbqt) primero.")
            return

        if not self._ligand_pdbqt_path:
            QMessageBox.warning(
                self, "Falta ligando",
                "Genera primero el PDBQT del ligando con el botón "
                "'Generar PDBQT del ligando'."
            )
            return

        center = (self._sb_center_x.value(), self._sb_center_y.value(), self._sb_center_z.value())
        box_size = (self._sb_size_x.value(), self._sb_size_y.value(), self._sb_size_z.value())
        exhaustiveness = self._sb_exhaustiveness.value()
        num_modes = self._sb_num_modes.value()
        vina_executable = self._vina_path_edit.text().strip() or None

        out_name = f"piapime_docking_out_{uuid.uuid4().hex[:8]}.pdbqt"
        output_pdbqt = str(Path(tempfile.gettempdir()) / out_name)

        self._btn_run.setEnabled(False)
        self._btn_run.setText("Ejecutando docking...")

        self._worker = _DockingWorker(
            receptor, self._ligand_pdbqt_path, output_pdbqt,
            center, box_size, exhaustiveness, num_modes, vina_executable,
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_docking_finished)
        self._worker.error.connect(self._on_docking_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)

        self._thread.start()

    def _cleanup_thread(self) -> None:
        self._btn_run.setEnabled(True)
        self._btn_run.setText("Ejecutar Docking")
        self._thread = None
        self._worker = None

    def _on_docking_finished(self, result: DockingResult) -> None:
        if not result.success:
            QMessageBox.critical(self, "Error de docking", result.error)
            self._log_text.setPlainText(result.log_text or result.error)
            return

        self._output_pdbqt_path = result.output_pdbqt_path
        self._populate_poses_table(result)
        self._log_text.setPlainText(result.log_text)
        self._output_path_label.setText(f"Archivo de salida: {result.output_pdbqt_path}")

        if not result.poses:
            QMessageBox.information(
                self, "Sin poses",
                "Vina terminó sin error, pero no se pudieron extraer poses "
                "del log. Revisa el log crudo para más detalles."
            )
            return

        self._update_3d_view(result)

    def _on_docking_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Error inesperado de docking", msg)

    def _populate_poses_table(self, result: DockingResult) -> None:
        self._poses_table.setRowCount(len(result.poses))
        for row, pose in enumerate(result.poses):
            values = [str(pose.rank), f"{pose.affinity_kcal_mol:.2f}",
                      f"{pose.rmsd_lb:.3f}", f"{pose.rmsd_ub:.3f}"]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._poses_table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Visualización 3D (py3Dmol vía QWebEngineView, opcional)
    # ------------------------------------------------------------------

    def _update_3d_view(self, result: DockingResult) -> None:
        if not _WEBENGINE_AVAILABLE or self._web_view is None:
            return

        try:
            receptor_path = self._receptor_edit.text().strip()
            receptor_text = Path(receptor_path).read_text(errors="ignore") if receptor_path else ""
            pose_text = Path(result.output_pdbqt_path).read_text(errors="ignore")
        except Exception as e:
            QMessageBox.warning(
                self, "Visualización 3D",
                f"No se pudieron leer los archivos PDBQT para la visualización: {e}"
            )
            return

        html = self._build_py3dmol_html(receptor_text, pose_text)
        try:
            self._web_view.setHtml(html)
        except Exception as e:
            QMessageBox.warning(
                self, "Visualización 3D",
                f"No se pudo renderizar la visualización 3D: {e}"
            )

    @staticmethod
    def _build_py3dmol_html(receptor_pdbqt_text: str, pose_pdbqt_text: str) -> str:
        """Genera un HTML autocontenido que carga py3Dmol desde un CDN y
        renderiza el receptor (gris, cartoon/líneas) y la mejor pose del
        ligando (esferas/varillas coloreadas)."""
        receptor_js = receptor_pdbqt_text.replace("\\", "\\\\").replace("`", "\\`")
        pose_js = pose_pdbqt_text.replace("\\", "\\\\").replace("`", "\\`")
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://3dmol.org/build/3Dmol-min.js"></script>
<style>
  body {{ margin: 0; background-color: #1e1e2e; }}
  #viewer {{ width: 100%; height: 100vh; position: relative; }}
</style>
</head>
<body>
<div id="viewer"></div>
<script>
  var viewer = $3Dmol.createViewer("viewer", {{backgroundColor: "#1e1e2e"}});
  var receptorData = `{receptor_js}`;
  var ligandData = `{pose_js}`;
  if (receptorData.trim().length > 0) {{
    var receptorModel = viewer.addModel(receptorData, "pdbqt");
    receptorModel.setStyle({{}}, {{cartoon: {{color: "spectrum"}}, line: {{colorscheme: "grayCarbon"}}}});
  }}
  var ligandModel = viewer.addModel(ligandData, "pdbqt");
  ligandModel.setStyle({{}}, {{stick: {{colorscheme: "cyanCarbon"}}}});
  viewer.zoomTo();
  viewer.render();
</script>
</body>
</html>"""
