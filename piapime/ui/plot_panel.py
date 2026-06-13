"""Panel de visualización con matplotlib embebido en Qt."""

from __future__ import annotations

from typing import Optional

import numpy as np
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QLabel, QFrame,
)
from PySide6.QtCore import Qt

from piapime.models.fitting import FittingResult

# Paleta de colores para datasets
_COLOR_CYCLE = [
    "#89b4fa", "#a6e3a1", "#fab387", "#f38ba8",
    "#cba6f7", "#f9e2af", "#94e2d5", "#89dceb",
    "#1e66f5", "#40a02b", "#fe640b", "#d20f39",
]


class PlotPanel(QWidget):
    """Panel con canvas matplotlib y controles de visualización."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._datasets: dict[str, dict] = {}  # {name: {x, y, color, fit}}
        self._color_idx = 0
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Controles superiores
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self._chk_grid = QCheckBox("Cuadrícula")
        self._chk_grid.setChecked(True)
        self._chk_grid.toggled.connect(self.refresh_plot)

        self._chk_legend = QCheckBox("Leyenda")
        self._chk_legend.setChecked(True)
        self._chk_legend.toggled.connect(self.refresh_plot)

        self._chk_logx = QCheckBox("Escala Log X")
        self._chk_logx.setChecked(True)
        self._chk_logx.toggled.connect(self.refresh_plot)

        self._chk_logy = QCheckBox("Escala Log Y")
        self._chk_logy.setChecked(False)
        self._chk_logy.toggled.connect(self.refresh_plot)

        self._chk_ci = QCheckBox("Banda IC 95%")
        self._chk_ci.setChecked(True)
        self._chk_ci.toggled.connect(self.refresh_plot)

        self._chk_residuals = QCheckBox("Residuales")
        self._chk_residuals.setChecked(False)
        self._chk_residuals.toggled.connect(self._toggle_residuals)

        btn_reset = QPushButton("Restablecer Vista")
        btn_reset.clicked.connect(self._reset_view)

        btn_export = QPushButton("Exportar Figura")
        btn_export.clicked.connect(self._export_figure)

        for widget in [
            self._chk_logx, self._chk_logy,
            QFrame(),  # separador visual
            self._chk_grid, self._chk_legend, self._chk_ci, self._chk_residuals,
        ]:
            if isinstance(widget, QFrame):
                widget.setFrameShape(QFrame.Shape.VLine)
                ctrl_layout.addWidget(widget)
            else:
                ctrl_layout.addWidget(widget)

        ctrl_layout.addStretch()
        ctrl_layout.addWidget(btn_reset)
        ctrl_layout.addWidget(btn_export)
        layout.addLayout(ctrl_layout)

        # Canvas matplotlib
        self._fig = Figure(figsize=(8, 5), dpi=100, facecolor="#1e1e2e")
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setMinimumHeight(350)

        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        self._toolbar.setStyleSheet(
            "QToolBar { background: #181825; border: none; }"
            "QToolButton { color: #cdd6f4; background: transparent; border: none; padding: 4px; }"
            "QToolButton:hover { background: #313244; border-radius: 4px; }"
        )

        layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas)

        # Crear ejes iniciales
        self._init_axes()

    def _init_axes(self) -> None:
        """Inicializa los subplots."""
        self._fig.clear()
        if self._chk_residuals.isChecked():
            self._ax = self._fig.add_subplot(211)
            self._ax_res = self._fig.add_subplot(212)
        else:
            self._ax = self._fig.add_subplot(111)
            self._ax_res = None
        self._style_axes()

    def _style_axes(self) -> None:
        bg = "#1e1e2e"
        fg = "#cdd6f4"
        grid_color = "#313244"

        for ax in [a for a in [self._ax, getattr(self, "_ax_res", None)] if a]:
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=9)
            ax.spines["bottom"].set_color("#45475a")
            ax.spines["left"].set_color("#45475a")
            ax.spines["top"].set_color("#45475a")
            ax.spines["right"].set_color("#45475a")
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            ax.title.set_color(fg)

        self._fig.patch.set_facecolor(bg)
        self._fig.subplots_adjust(left=0.1, right=0.97, top=0.93, bottom=0.12, hspace=0.35)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def next_color(self) -> str:
        color = _COLOR_CYCLE[self._color_idx % len(_COLOR_CYCLE)]
        self._color_idx += 1
        return color

    def plot_data(self, name: str, x: np.ndarray, y: np.ndarray,
                  color: Optional[str] = None) -> None:
        if color is None:
            if name in self._datasets:
                color = self._datasets[name].get("color", self.next_color())
            else:
                color = self.next_color()
        if name not in self._datasets:
            self._datasets[name] = {}
        self._datasets[name]["x"] = x
        self._datasets[name]["y"] = y
        self._datasets[name]["color"] = color
        self.refresh_plot()

    def plot_fit(self, name: str, result: FittingResult) -> None:
        if name not in self._datasets:
            self._datasets[name] = {"color": self.next_color()}
        self._datasets[name]["fit"] = result
        self.refresh_plot()

    def clear_dataset(self, name: str) -> None:
        self._datasets.pop(name, None)
        self.refresh_plot()

    def clear_all(self) -> None:
        self._datasets.clear()
        self._color_idx = 0
        self.refresh_plot()

    def get_color(self, name: str) -> str:
        return self._datasets.get(name, {}).get("color", "#89b4fa")

    # ------------------------------------------------------------------
    # Renderizado
    # ------------------------------------------------------------------

    def refresh_plot(self) -> None:
        self._init_axes()
        ax = self._ax

        has_data = False
        for name, ds in self._datasets.items():
            color = ds.get("color", "#89b4fa")
            x = ds.get("x")
            y = ds.get("y")
            fit: Optional[FittingResult] = ds.get("fit")

            if x is not None and y is not None and len(x) > 0:
                ax.scatter(x, y, color=color, s=60, zorder=5,
                           label=f"{name} (datos)", edgecolors="white", linewidths=0.5)
                has_data = True

            if fit is not None and fit.success and len(fit.x_fit) > 0:
                ax.plot(fit.x_fit, fit.y_fit, color=color, linewidth=2,
                        label=f"{name} ({fit.model_name})", zorder=4)

                if (self._chk_ci.isChecked()
                        and fit.y_fit_lower is not None
                        and fit.y_fit_upper is not None):
                    ax.fill_between(
                        fit.x_fit, fit.y_fit_lower, fit.y_fit_upper,
                        alpha=0.2, color=color, label="_nolegend_"
                    )

                if self._ax_res is not None and x is not None and len(x) > 0:
                    self._ax_res.axhline(0, color="#45475a", linewidth=1, linestyle="--")
                    self._ax_res.scatter(
                        x[np.isfinite(x) & (x > 0)],
                        fit.residuals,
                        color=color, s=50, zorder=5
                    )

        # Escala de ejes
        if self._chk_logx.isChecked():
            ax.set_xscale("log")
        else:
            ax.set_xscale("linear")

        if self._chk_logy.isChecked():
            ax.set_yscale("log")
        else:
            ax.set_yscale("linear")

        # Cuadrícula
        if self._chk_grid.isChecked():
            ax.grid(True, color="#313244", linewidth=0.7, linestyle="--", alpha=0.8)
            ax.minorticks_on()
            ax.grid(True, which="minor", color="#252535", linewidth=0.4, linestyle=":")
        else:
            ax.grid(False)

        # Leyenda
        if self._chk_legend.isChecked() and has_data:
            leg = ax.legend(
                facecolor="#313244", edgecolor="#45475a",
                labelcolor="#cdd6f4", fontsize=9,
            )
            leg.get_frame().set_linewidth(0.5)

        # Etiquetas
        ax.set_xlabel("Concentración (Dosis)", fontsize=10)
        ax.set_ylabel("Respuesta (%)", fontsize=10)
        ax.set_title("Curva Dosis-Respuesta", fontsize=12, pad=10)

        if self._ax_res is not None:
            self._ax_res.set_xlabel("Concentración", fontsize=9)
            self._ax_res.set_ylabel("Residuales", fontsize=9)
            self._ax_res.set_title("Residuales", fontsize=10)
            if self._chk_logx.isChecked():
                self._ax_res.set_xscale("log")

        self._style_axes()
        self._canvas.draw()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _toggle_residuals(self) -> None:
        self.refresh_plot()

    def _reset_view(self) -> None:
        if self._ax:
            self._ax.autoscale()
        self._canvas.draw()

    def _export_figure(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar figura", "curva_dosis_respuesta",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;TIFF (*.tiff)"
        )
        if path:
            self._fig.savefig(path, dpi=300, bbox_inches="tight",
                              facecolor=self._fig.get_facecolor())
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Exportar", f"Figura guardada en:\n{path}")

    def export_figure(self, path: str) -> None:
        self._fig.savefig(path, dpi=300, bbox_inches="tight",
                          facecolor=self._fig.get_facecolor())
