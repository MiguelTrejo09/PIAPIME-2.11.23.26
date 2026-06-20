"""Panel de Mecanismo de Acción — diagramas de vías de señalización
farmacológica, completamente offline (sin internet, sin IA generativa).

Renderiza diagramas de flujo verticales con matplotlib usando el mismo
patrón visual (_new_canvas/_style_axes) que pkpd_panel.py.
"""

from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QTextEdit, QGroupBox, QFrame, QSplitter,
)

from piapime.mechanism.pathways import (
    Pathway, get_pathway, get_pathway_names, search_pathways_by_drug,
)


def _new_canvas(figsize=(7, 8)):
    """Crea un canvas matplotlib embebido siguiendo el estilo de pkpd_panel.py."""
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


_ALL_CATEGORIES_LABEL = "Todas"


class MechanismPanel(QWidget):
    """Panel de diagramas de Mecanismo de Acción (offline, matplotlib)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_pathway: Optional[Pathway] = None
        self._setup_ui()
        if self._pathway_combo.count() > 0:
            self._on_pathway_changed(self._pathway_combo.currentText())

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        title = QLabel("Mecanismo de Acción — Vías de Señalización Farmacológica")
        title.setObjectName("labelTitle")
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Diagramas didácticos generados a partir de un conjunto de datos "
            "local (sin conexión a internet ni inteligencia artificial "
            "generativa). Contenido de nivel de farmacología general."
        )
        subtitle.setObjectName("labelSubtitle")
        subtitle.setWordWrap(True)
        main_layout.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(sep)

        # ── Controles de selección ────────────────────────────────────
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Categoría:"))
        self._category_combo = QComboBox()
        self._category_combo.addItem(_ALL_CATEGORIES_LABEL)
        categories = sorted({get_pathway(name).category for name in get_pathway_names()})
        for cat in categories:
            self._category_combo.addItem(cat)
        self._category_combo.currentTextChanged.connect(self._on_category_filter_changed)
        controls_layout.addWidget(self._category_combo)

        controls_layout.addWidget(QLabel("Vía:"))
        self._pathway_combo = QComboBox()
        self._pathway_combo.addItems(get_pathway_names())
        self._pathway_combo.currentTextChanged.connect(self._on_pathway_changed)
        controls_layout.addWidget(self._pathway_combo, 1)

        controls_layout.addWidget(QLabel("Buscar por fármaco:"))
        self._drug_search_edit = QLineEdit()
        self._drug_search_edit.setPlaceholderText("Ej. morfina, ibuprofeno...")
        self._drug_search_edit.returnPressed.connect(self._on_drug_search)
        controls_layout.addWidget(self._drug_search_edit, 1)

        btn_search = QPushButton("Buscar")
        btn_search.clicked.connect(self._on_drug_search)
        controls_layout.addWidget(btn_search)

        main_layout.addLayout(controls_layout)

        self._category_label = QLabel("Categoría: N/A")
        self._category_label.setObjectName("labelSubtitle")
        main_layout.addWidget(self._category_label)

        # ── Cuerpo: diagrama + descripción ────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._fig, self._canvas, self._toolbar = _new_canvas()
        self._ax = self._fig.add_subplot(111)
        _style_axes(self._fig, self._ax)

        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self._toolbar)
        canvas_layout.addWidget(self._canvas)
        splitter.addWidget(canvas_container)

        info_group = QGroupBox("Descripción del Mecanismo")
        info_layout = QVBoxLayout(info_group)
        self._info_text = QTextEdit()
        self._info_text.setReadOnly(True)
        info_layout.addWidget(self._info_text)
        splitter.addWidget(info_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # Filtrado por categoría
    # ------------------------------------------------------------------

    def _on_category_filter_changed(self, category: str) -> None:
        current = self._pathway_combo.currentText()
        self._pathway_combo.blockSignals(True)
        self._pathway_combo.clear()
        for name in get_pathway_names():
            if category == _ALL_CATEGORIES_LABEL or get_pathway(name).category == category:
                self._pathway_combo.addItem(name)
        self._pathway_combo.blockSignals(False)

        idx = self._pathway_combo.findText(current)
        if idx >= 0:
            self._pathway_combo.setCurrentIndex(idx)
        elif self._pathway_combo.count() > 0:
            self._pathway_combo.setCurrentIndex(0)
            self._on_pathway_changed(self._pathway_combo.currentText())

    # ------------------------------------------------------------------
    # Búsqueda por fármaco
    # ------------------------------------------------------------------

    def _on_drug_search(self) -> None:
        query = self._drug_search_edit.text().strip()
        if not query:
            return
        results = search_pathways_by_drug(query)
        if not results:
            self._info_text.setPlainText(
                f"No se encontraron vías que mencionen el fármaco '{query}' "
                "en este conjunto de datos local."
            )
            return
        # Selecciona la primera vía encontrada en el combo (restableciendo
        # el filtro de categoría a "Todas" para asegurar que esté visible).
        self._category_combo.setCurrentText(_ALL_CATEGORIES_LABEL)
        idx = self._pathway_combo.findText(results[0].name)
        if idx >= 0:
            self._pathway_combo.setCurrentIndex(idx)
            self._on_pathway_changed(results[0].name)

    # ------------------------------------------------------------------
    # Selección de vía y dibujo
    # ------------------------------------------------------------------

    def _on_pathway_changed(self, name: str) -> None:
        if not name:
            return
        try:
            pathway = get_pathway(name)
        except KeyError:
            return
        self._current_pathway = pathway
        self._category_label.setText(f"Categoría: {pathway.category}")
        self._draw_pathway(pathway)
        self._update_info_text(pathway)

    def _update_info_text(self, pathway: Pathway) -> None:
        lines = [f"<b>{pathway.name}</b> ({pathway.category})", ""]
        lines.append(pathway.overall_description)
        lines.append("")
        lines.append("<b>Fármacos de ejemplo:</b> " + ", ".join(pathway.drugs_example))
        lines.append("")
        lines.append("<b>Pasos de la vía:</b>")
        for i, step in enumerate(pathway.steps, start=1):
            lines.append(f"{i}. <b>{step.label}:</b> {step.description}")
        self._info_text.setHtml("<br>".join(lines))

    def _draw_pathway(self, pathway: Pathway) -> None:
        n = len(pathway.steps)
        # Reajusta la altura de la figura en función del número de pasos.
        fig_height = max(4.0, 1.3 * n)
        self._fig.set_size_inches(7.0, fig_height, forward=True)

        self._ax.clear()
        self._ax.set_xlim(0, 10)
        self._ax.set_ylim(0, n)
        self._ax.axis("off")

        box_color = "#313244"
        edge_color = "#89b4fa"
        text_color = "#cdd6f4"

        box_width = 8.0
        box_height = 0.7
        x0 = (10 - box_width) / 2.0

        centers_y = []
        for i, step in enumerate(pathway.steps):
            # y crece hacia abajo: el primer paso arriba, el último abajo.
            y_center = n - i - 0.5
            y0 = y_center - box_height / 2.0
            centers_y.append(y_center)

            box = FancyBboxPatch(
                (x0, y0), box_width, box_height,
                boxstyle="round,pad=0.02,rounding_size=0.12",
                linewidth=1.8, edgecolor=edge_color, facecolor=box_color,
                mutation_aspect=1.0,
            )
            self._ax.add_patch(box)

            self._ax.text(
                5.0, y_center, step.label,
                ha="center", va="center", color=text_color,
                fontsize=9.5, fontweight="bold", wrap=True,
            )

            if i > 0:
                y_prev = centers_y[i - 1] - box_height / 2.0
                y_curr = y_center + box_height / 2.0
                self._ax.annotate(
                    "", xy=(5.0, y_curr), xytext=(5.0, y_prev),
                    arrowprops=dict(arrowstyle="-|>", color="#a6e3a1",
                                     linewidth=2.0, mutation_scale=18),
                )

        self._ax.set_title(pathway.name, color=text_color, fontsize=12, fontweight="bold")
        _style_axes(self._fig, self._ax)
        self._fig.subplots_adjust(left=0.03, right=0.97, top=0.95, bottom=0.03)
        self._canvas.draw()
