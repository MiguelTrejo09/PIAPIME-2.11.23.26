"""Panel de resultados del ajuste de curvas dosis-respuesta."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QTextEdit, QTabWidget,
)

from piapime.models.fitting import FittingResult


def _fmt(value: float, decimals: int = 6) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    if abs(value) < 1e-3 or abs(value) > 1e6:
        return f"{value:.4e}"
    return f"{value:.{decimals}f}"


class ResultsPanel(QWidget):
    """Panel que muestra los resultados de ajuste de curvas dosis-respuesta."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: dict[str, FittingResult] = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Título
        title_row = QHBoxLayout()
        title = QLabel("Resultados del Ajuste")
        title.setObjectName("labelTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        btn_copy = QPushButton("Copiar Todo")
        btn_copy.setToolTip("Copia todos los resultados al portapapeles")
        btn_copy.clicked.connect(self._copy_all)
        title_row.addWidget(btn_copy)

        btn_clear_res = QPushButton("Limpiar")
        btn_clear_res.setToolTip("Elimina los resultados mostrados")
        btn_clear_res.clicked.connect(self.clear_all)
        title_row.addWidget(btn_clear_res)
        layout.addLayout(title_row)

        # Tabs por dataset
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Mensaje inicial
        self._empty_label = QLabel(
            "No hay resultados aún.\n\nConfigura un modelo y presiona 'Ajustar Curva'."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("labelSubtitle")
        self._tabs.addTab(self._empty_label, "Sin resultados")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def show_result(self, dataset_name: str, result: FittingResult,
                    color: str = "#89b4fa") -> None:
        """Muestra o actualiza el resultado de un dataset."""
        self._results[dataset_name] = result

        # Buscar tab existente
        for i in range(self._tabs.count()):
            if self._tabs.tabText(i) == dataset_name:
                widget = self._build_result_widget(result, color)
                self._tabs.removeTab(i)
                self._tabs.insertTab(i, widget, dataset_name)
                self._tabs.setCurrentIndex(i)
                return

        # Eliminar el tab vacío inicial
        if self._tabs.count() == 1 and self._tabs.tabText(0) == "Sin resultados":
            self._tabs.removeTab(0)

        widget = self._build_result_widget(result, color)
        idx = self._tabs.addTab(widget, dataset_name)
        self._tabs.setCurrentIndex(idx)

    def remove_result(self, dataset_name: str) -> None:
        for i in range(self._tabs.count()):
            if self._tabs.tabText(i) == dataset_name:
                self._tabs.removeTab(i)
                self._results.pop(dataset_name, None)
                break
        if self._tabs.count() == 0:
            self._tabs.addTab(self._empty_label, "Sin resultados")

    def clear_all(self) -> None:
        self._results.clear()
        self._tabs.clear()
        self._tabs.addTab(self._empty_label, "Sin resultados")

    # ------------------------------------------------------------------
    # Construcción del widget de resultado
    # ------------------------------------------------------------------

    def _build_result_widget(self, result: FittingResult, color: str) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        if not result.success:
            err = QLabel(f"El ajuste falló:\n{result.message}")
            err.setStyleSheet("color: #f38ba8; font-size: 13px;")
            err.setWordWrap(True)
            layout.addWidget(err)
            layout.addStretch()
            scroll.setWidget(container)
            return scroll

        # ── EC50 destacado ──────────────────────────────────────────
        ec50_frame = QFrame()
        ec50_frame.setStyleSheet(
            f"QFrame {{ border: 2px solid {color}; border-radius: 8px; "
            f"background: rgba(30,30,46,0.8); padding: 8px; }}"
        )
        ec50_layout = QVBoxLayout(ec50_frame)
        ec50_layout.setSpacing(4)

        ec50_title = QLabel("EC₅₀ / IC₅₀")
        ec50_title.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
        ec50_layout.addWidget(ec50_title)

        ec50_value = QLabel(_fmt(result.ec50))
        ec50_value.setObjectName("labelEC50")
        ec50_value.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        ec50_layout.addWidget(ec50_value)

        lo, hi = result.ec50_ci
        ci_text = f"IC 95%: [{_fmt(lo)}, {_fmt(hi)}]"
        ec50_ci_label = QLabel(ci_text)
        ec50_ci_label.setObjectName("labelSubtitle")
        ec50_layout.addWidget(ec50_ci_label)

        layout.addWidget(ec50_frame)

        # ── Estadísticas de ajuste ──────────────────────────────────
        stats_label = QLabel("Estadísticas de Ajuste")
        stats_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        layout.addWidget(stats_label)

        stats_table = QTableWidget(4, 2)
        stats_table.setHorizontalHeaderLabels(["Estadística", "Valor"])
        stats_table.horizontalHeader().setStretchLastSection(True)
        stats_table.verticalHeader().setVisible(False)
        stats_table.setMaximumHeight(160)
        stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        stats_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        stats_data = [
            ("R²", _fmt(result.r_squared, 6)),
            ("RMSE", _fmt(result.rmse, 6)),
            ("AIC", _fmt(result.aic, 4)),
            ("BIC", _fmt(result.bic, 4)),
        ]
        for row, (stat, val) in enumerate(stats_data):
            s_item = QTableWidgetItem(stat)
            v_item = QTableWidgetItem(val)
            s_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            v_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            v_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            stats_table.setItem(row, 0, s_item)
            stats_table.setItem(row, 1, v_item)

        layout.addWidget(stats_table)

        # ── Parámetros ──────────────────────────────────────────────
        params_label = QLabel("Parámetros del Modelo")
        params_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        layout.addWidget(params_label)

        n_params = len(result.parameters)
        params_table = QTableWidget(n_params, 5)
        params_table.setHorizontalHeaderLabels(
            ["Parámetro", "Valor", "Error Estándar", "IC 95% Inf.", "IC 95% Sup."]
        )
        params_table.horizontalHeader().setStretchLastSection(True)
        params_table.verticalHeader().setVisible(False)
        params_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        params_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        params_table.setMaximumHeight(40 + n_params * 30)

        for row, (pname, pval) in enumerate(result.parameters.items()):
            perr = result.param_errors.get(pname, float("nan"))
            ci = result.ci_95.get(pname, (float("nan"), float("nan")))
            items = [
                QTableWidgetItem(pname),
                QTableWidgetItem(_fmt(pval)),
                QTableWidgetItem(_fmt(perr)),
                QTableWidgetItem(_fmt(ci[0])),
                QTableWidgetItem(_fmt(ci[1])),
            ]
            for col, item in enumerate(items):
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if col > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                params_table.setItem(row, col, item)

        layout.addWidget(params_table)

        # ── Modelo y mensaje ────────────────────────────────────────
        model_info = QLabel(f"Modelo: <b>{result.model_name}</b>  •  {result.message}")
        model_info.setObjectName("labelSubtitle")
        model_info.setWordWrap(True)
        layout.addWidget(model_info)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------
    # Copiar resultados
    # ------------------------------------------------------------------

    def _copy_all(self) -> None:
        lines = []
        for name, result in self._results.items():
            lines.append(f"=== {name} ===")
            lines.append(f"Modelo: {result.model_name}")
            lines.append(f"R²: {_fmt(result.r_squared)}")
            lines.append(f"RMSE: {_fmt(result.rmse)}")
            lines.append(f"AIC: {_fmt(result.aic)}")
            lines.append(f"BIC: {_fmt(result.bic)}")
            lines.append(f"EC50: {_fmt(result.ec50)}")
            lo, hi = result.ec50_ci
            lines.append(f"EC50 IC 95%: [{_fmt(lo)}, {_fmt(hi)}]")
            lines.append("")
            lines.append("Parámetro\tValor\tError Estándar\tIC95 Inf.\tIC95 Sup.")
            for pname, pval in result.parameters.items():
                perr = result.param_errors.get(pname, float("nan"))
                ci = result.ci_95.get(pname, (float("nan"), float("nan")))
                lines.append(f"{pname}\t{_fmt(pval)}\t{_fmt(perr)}\t{_fmt(ci[0])}\t{_fmt(ci[1])}")
            lines.append("")
        QGuiApplication.clipboard().setText("\n".join(lines))
