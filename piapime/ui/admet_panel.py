"""Panel ADMET ligero (descriptores RDKit offline, sin modelos de ML)."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QTextEdit,
    QFrame, QGridLayout,
)

from piapime.admet.descriptors import ADMETResult, compute_admet


_EXAMPLES = {
    "Aspirina": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "Cafeína": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "Ibuprofeno": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
}


def _fmt(value, decimals: int = 3) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{decimals}f}"


class ADMETPanel(QWidget):
    """Panel de descriptores ADMET offline basados en RDKit."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("ADMET — Descriptores Fisicoquímicos y Reglas (offline, sin ML)")
        title.setObjectName("labelTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Cálculo local con RDKit (sin conexión a internet ni modelos de "
            "aprendizaje automático). Las notas de absorción/BBB/P-gp son "
            "heurísticas aproximadas basadas en reglas de corte fisicoquímicas."
        )
        subtitle.setObjectName("labelSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # ── Entrada SMILES ───────────────────────────────────────────
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("SMILES:"))
        self._smiles_edit = QLineEdit()
        self._smiles_edit.setPlaceholderText("Ej. CC(=O)OC1=CC=CC=C1C(=O)O (Aspirina)")
        self._smiles_edit.returnPressed.connect(self._on_calculate)
        input_layout.addWidget(self._smiles_edit)

        btn_calc = QPushButton("Calcular")
        btn_calc.setObjectName("btnFit")
        btn_calc.clicked.connect(self._on_calculate)
        input_layout.addWidget(btn_calc)
        layout.addLayout(input_layout)

        # ── Botones de ejemplo ───────────────────────────────────────
        examples_layout = QHBoxLayout()
        examples_layout.addWidget(QLabel("Ejemplos:"))
        for name, smiles in _EXAMPLES.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked=False, s=smiles: self._load_example(s))
            examples_layout.addWidget(btn)
        examples_layout.addStretch()
        layout.addLayout(examples_layout)

        # ── Mensaje de error ──────────────────────────────────────────
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # ── Tabla de descriptores y semáforo de reglas ───────────────
        body_layout = QHBoxLayout()

        self._desc_table = QTableWidget(0, 2)
        self._desc_table.setHorizontalHeaderLabels(["Propiedad", "Valor"])
        self._desc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._desc_table.verticalHeader().setVisible(False)
        self._desc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        body_layout.addWidget(self._desc_table, 2)

        rules_group = QGroupBox("Reglas / Semáforo")
        rules_layout = QVBoxLayout(rules_group)

        self._lbl_lipinski = QLabel("Lipinski: N/A")
        self._lbl_veber = QLabel("Veber: N/A")
        self._lbl_egan = QLabel("Egan (heurística): N/A")
        for lbl in (self._lbl_lipinski, self._lbl_veber, self._lbl_egan):
            lbl.setStyleSheet(
                "padding: 8px; border-radius: 6px; font-weight: bold; "
                "background-color: #313244; color: #cdd6f4;"
            )
            rules_layout.addWidget(lbl)
        rules_layout.addStretch()
        body_layout.addWidget(rules_group, 1)

        layout.addLayout(body_layout)

        # ── Notas interpretativas ─────────────────────────────────────
        notes_group = QGroupBox("Notas Interpretativas")
        notes_layout = QVBoxLayout(notes_group)
        self._notes_text = QTextEdit()
        self._notes_text.setReadOnly(True)
        self._notes_text.setMaximumHeight(150)
        notes_layout.addWidget(self._notes_text)
        layout.addWidget(notes_group)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _load_example(self, smiles: str) -> None:
        self._smiles_edit.setText(smiles)
        self._on_calculate()

    def _on_calculate(self) -> None:
        smiles = self._smiles_edit.text().strip()
        if not smiles:
            return

        result = compute_admet(smiles)

        if not result.valid:
            self._error_label.setText(f"Error: {result.error}")
            self._error_label.setVisible(True)
            self._desc_table.setRowCount(0)
            self._notes_text.clear()
            self._reset_rule_labels()
            return

        self._error_label.setVisible(False)
        self._populate_descriptors(result)
        self._populate_rules(result)
        self._populate_notes(result)

    def _reset_rule_labels(self) -> None:
        for lbl, text in [
            (self._lbl_lipinski, "Lipinski: N/A"),
            (self._lbl_veber, "Veber: N/A"),
            (self._lbl_egan, "Egan (heurística): N/A"),
        ]:
            lbl.setText(text)
            lbl.setStyleSheet(
                "padding: 8px; border-radius: 6px; font-weight: bold; "
                "background-color: #313244; color: #cdd6f4;"
            )

    def _populate_descriptors(self, r: ADMETResult) -> None:
        rows = [
            ("Fórmula molecular", r.mol_formula),
            ("Peso molecular (g/mol)", _fmt(r.mw)),
            ("LogP (Crippen)", _fmt(r.logp)),
            ("TPSA (Å²)", _fmt(r.tpsa)),
            ("Donadores de H (HBD)", _fmt(r.hbd)),
            ("Aceptores de H (HBA)", _fmt(r.hba)),
            ("Enlaces rotables", _fmt(r.rotatable_bonds)),
            ("Anillos aromáticos", _fmt(r.aromatic_rings)),
            ("Átomos pesados", _fmt(r.heavy_atoms)),
            ("Fracción Csp3", _fmt(r.fraction_csp3)),
            ("Refractividad molar", _fmt(r.molar_refractivity)),
            ("Violaciones de Lipinski", _fmt(r.lipinski_violations)),
        ]
        self._desc_table.setRowCount(len(rows))
        for row, (prop, val) in enumerate(rows):
            p_item = QTableWidgetItem(prop)
            v_item = QTableWidgetItem(val)
            p_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            v_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            v_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._desc_table.setItem(row, 0, p_item)
            self._desc_table.setItem(row, 1, v_item)

    def _populate_rules(self, r: ADMETResult) -> None:
        green = "background-color: #2d4f2d; color: #a6e3a1;"
        red = "background-color: #4f2d36; color: #f38ba8;"
        base = "padding: 8px; border-radius: 6px; font-weight: bold; "

        self._lbl_lipinski.setText(
            f"Lipinski: {'✓' if r.lipinski_pass else '✗'} "
            f"({r.lipinski_violations} violación(es))"
        )
        self._lbl_lipinski.setStyleSheet(base + (green if r.lipinski_pass else red))

        self._lbl_veber.setText(f"Veber: {'✓' if r.veber_pass else '✗'}")
        self._lbl_veber.setStyleSheet(base + (green if r.veber_pass else red))

        self._lbl_egan.setText(f"Egan (heurística): {'✓' if r.egan_pass else '✗'}")
        self._lbl_egan.setStyleSheet(base + (green if r.egan_pass else red))

    def _populate_notes(self, r: ADMETResult) -> None:
        text = (
            f"Nota (heurística aproximada) — Absorción:\n{r.absorption_note}\n\n"
            f"Nota (heurística aproximada) — Barrera hematoencefálica (BBB):\n{r.bbb_note}\n\n"
            f"Nota (heurística aproximada) — Sustrato de P-glicoproteína (P-gp):\n{r.pgp_substrate_risk}"
        )
        self._notes_text.setPlainText(text)
