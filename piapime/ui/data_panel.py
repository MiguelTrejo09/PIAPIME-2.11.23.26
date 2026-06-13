"""Panel de entrada de datos dosis-respuesta."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QHeaderView,
    QShortcut, QFrame,
)

from piapime.utils.io_utils import read_csv, read_excel, validate_data


_DEFAULT_X = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
_DEFAULT_Y = [98.2, 97.5, 95.1, 88.4, 72.3, 49.8, 28.1, 12.4, 4.2, 1.8]


class DataPanel(QWidget):
    """Widget para ingresar/importar datos dosis-respuesta."""

    data_changed = Signal(np.ndarray, np.ndarray)  # x, y arrays

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._building = False
        self._setup_ui()
        self._load_defaults()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Título
        title = QLabel("Datos Experimentales")
        title.setObjectName("labelTitle")
        layout.addWidget(title)

        subtitle = QLabel("Ingresa las concentraciones (Dosis) y respuestas, o importa desde archivo.")
        subtitle.setObjectName("labelSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Tabla
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Concentración (Dosis)", "Respuesta (%)"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        # Botones de filas
        row_btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ Agregar Fila")
        btn_add.setToolTip("Agrega una fila vacía al final de la tabla")
        btn_add.clicked.connect(self._add_row)

        btn_remove = QPushButton("− Eliminar Fila")
        btn_remove.setToolTip("Elimina la(s) fila(s) seleccionada(s)")
        btn_remove.clicked.connect(self._remove_selected_rows)

        btn_clear = QPushButton("Limpiar Tabla")
        btn_clear.setObjectName("btnDanger")
        btn_clear.setToolTip("Elimina todos los datos de la tabla")
        btn_clear.clicked.connect(self._clear_table)

        row_btn_layout.addWidget(btn_add)
        row_btn_layout.addWidget(btn_remove)
        row_btn_layout.addStretch()
        row_btn_layout.addWidget(btn_clear)
        layout.addLayout(row_btn_layout)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        # Botones de importación
        import_label = QLabel("Importar desde archivo:")
        import_label.setObjectName("labelSubtitle")
        layout.addWidget(import_label)

        import_layout = QHBoxLayout()
        btn_csv = QPushButton("Importar CSV")
        btn_csv.setToolTip("Importa datos desde un archivo CSV (columnas: Dosis, Respuesta)")
        btn_csv.clicked.connect(self._import_csv)

        btn_excel = QPushButton("Importar Excel")
        btn_excel.setToolTip("Importa datos desde un archivo Excel (.xlsx)")
        btn_excel.clicked.connect(self._import_excel)

        btn_sample = QPushButton("Cargar Ejemplo")
        btn_sample.setToolTip("Carga datos de ejemplo para demostración")
        btn_sample.clicked.connect(self._load_defaults)

        import_layout.addWidget(btn_csv)
        import_layout.addWidget(btn_excel)
        import_layout.addWidget(btn_sample)
        layout.addLayout(import_layout)

        # Estado de validación
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Accesos rápidos de teclado
        QShortcut(QKeySequence("Ctrl+V"), self._table).activated.connect(self._paste_from_clipboard)
        QShortcut(QKeySequence("Delete"), self._table).activated.connect(self._remove_selected_rows)

    # ------------------------------------------------------------------
    # Datos por defecto
    # ------------------------------------------------------------------

    def _load_defaults(self) -> None:
        self._populate_table(_DEFAULT_X, _DEFAULT_Y)

    # ------------------------------------------------------------------
    # Manipulación de la tabla
    # ------------------------------------------------------------------

    def _add_row(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(""))
        self._table.setItem(row, 1, QTableWidgetItem(""))

    def _remove_selected_rows(self) -> None:
        selected = sorted({idx.row() for idx in self._table.selectedIndexes()}, reverse=True)
        if not selected:
            current = self._table.currentRow()
            if current >= 0:
                selected = [current]
        for row in selected:
            self._table.removeRow(row)
        self._emit_data()

    def _clear_table(self) -> None:
        reply = QMessageBox.question(
            self, "Limpiar tabla",
            "¿Seguro que deseas eliminar todos los datos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._table.setRowCount(0)
            self._emit_data()

    def _populate_table(self, x_vals: list, y_vals: list) -> None:
        self._building = True
        self._table.setRowCount(0)
        for xv, yv in zip(x_vals, y_vals):
            row = self._table.rowCount()
            self._table.insertRow(row)
            ix = QTableWidgetItem(str(xv))
            iy = QTableWidgetItem(str(yv))
            ix.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            iy.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, ix)
            self._table.setItem(row, 1, iy)
        self._building = False
        self._emit_data()

    # ------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir CSV", "", "Archivos CSV (*.csv *.txt);;Todos (*.*)"
        )
        if not path:
            return
        try:
            df = read_csv(path)
            x, y = self._extract_xy(df)
            self._populate_table(x.tolist(), y.tolist())
        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Excel", "", "Archivos Excel (*.xlsx *.xls);;Todos (*.*)"
        )
        if not path:
            return
        try:
            df = read_excel(path)
            x, y = self._extract_xy(df)
            self._populate_table(x.tolist(), y.tolist())
        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))

    @staticmethod
    def _extract_xy(df) -> tuple:
        import pandas as pd
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if len(numeric_cols) < 2:
            numeric_cols = df.columns.tolist()[:2]
        x = pd.to_numeric(df[numeric_cols[0]], errors="coerce").dropna().values
        y = pd.to_numeric(df[numeric_cols[1]], errors="coerce").dropna().values
        n = min(len(x), len(y))
        return x[:n], y[:n]

    # ------------------------------------------------------------------
    # Portapapeles (pegar desde Excel)
    # ------------------------------------------------------------------

    def _paste_from_clipboard(self) -> None:
        from PySide6.QtGui import QGuiApplication
        text = QGuiApplication.clipboard().text()
        if not text:
            return
        rows = text.strip().split("\n")
        x_vals, y_vals = [], []
        for row in rows:
            parts = row.replace(",", ".").split("\t")
            if len(parts) >= 2:
                try:
                    x_vals.append(float(parts[0].strip()))
                    y_vals.append(float(parts[1].strip()))
                except ValueError:
                    pass
        if x_vals:
            self._populate_table(x_vals, y_vals)

    # ------------------------------------------------------------------
    # Obtener datos actuales
    # ------------------------------------------------------------------

    def get_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Retorna (x, y) como arrays de numpy con valores válidos."""
        x_vals, y_vals = [], []
        for row in range(self._table.rowCount()):
            ix = self._table.item(row, 0)
            iy = self._table.item(row, 1)
            if ix is None or iy is None:
                continue
            try:
                xv = float(ix.text().replace(",", "."))
                yv = float(iy.text().replace(",", "."))
                if np.isfinite(xv) and np.isfinite(yv):
                    x_vals.append(xv)
                    y_vals.append(yv)
            except ValueError:
                pass
        return np.array(x_vals), np.array(y_vals)

    def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
        """Carga datos en la tabla."""
        self._populate_table(x.tolist(), y.tolist())

    # ------------------------------------------------------------------
    # Señal de datos cambiados
    # ------------------------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._building:
            self._emit_data()

    def _emit_data(self) -> None:
        x, y = self.get_data()
        ok, msg = validate_data(x, y)
        if ok:
            self._status_label.setText(
                f"<span style='color:#a6e3a1;'>✓ {len(x)} puntos válidos</span>"
            )
            self.data_changed.emit(x, y)
        else:
            self._status_label.setText(
                f"<span style='color:#f38ba8;'>⚠ {msg}</span>"
            )
