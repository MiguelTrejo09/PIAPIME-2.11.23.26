"""Temas visuales para PIAPIME."""

DARK_STYLESHEET = """
/* ── Ventana principal ─────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 13px;
}

/* ── Menú ──────────────────────────────────────────────────────── */
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #313244;
    border-radius: 4px;
}
QMenu {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QMenu::item:selected {
    background-color: #313244;
}
QMenu::separator {
    height: 1px;
    background: #45475a;
    margin: 2px 8px;
}

/* ── Barra de herramientas ─────────────────────────────────────── */
QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #45475a;
    spacing: 4px;
    padding: 2px 4px;
}
QToolButton {
    background-color: transparent;
    color: #cdd6f4;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
}
QToolButton:hover {
    background-color: #313244;
}
QToolButton:pressed {
    background-color: #45475a;
}

/* ── Pestañas ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #45475a;
    background-color: #1e1e2e;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #181825;
    color: #6c7086;
    padding: 6px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #313244;
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}

/* ── Tabla ─────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    gridline-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    selection-background-color: #45475a;
}
QTableWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QHeaderView::section {
    background-color: #313244;
    color: #89b4fa;
    padding: 6px;
    border: none;
    border-right: 1px solid #45475a;
    font-weight: bold;
}
QTableCornerButton::section {
    background-color: #313244;
}

/* ── Lista ─────────────────────────────────────────────────────── */
QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QListWidget::item:hover {
    background-color: #313244;
}

/* ── Botones ───────────────────────────────────────────────────── */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton#btnFit {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
    font-size: 14px;
    min-height: 36px;
    border: none;
}
QPushButton#btnFit:hover {
    background-color: #b4d0ff;
}
QPushButton#btnFitAll {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
    min-height: 32px;
}
QPushButton#btnFitAll:hover {
    background-color: #c5f5c0;
}
QPushButton#btnDanger {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
}
QPushButton#btnDanger:hover {
    background-color: #f5a0b5;
}

/* ── ComboBox ──────────────────────────────────────────────────── */
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 26px;
}
QComboBox:hover {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #181825;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
}

/* ── SpinBox ───────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 26px;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #89b4fa;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #45475a;
    border: none;
    border-radius: 3px;
    width: 16px;
}

/* ── CheckBox ──────────────────────────────────────────────────── */
QCheckBox {
    color: #cdd6f4;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #45475a;
    border-radius: 3px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* ── LineEdit ──────────────────────────────────────────────────── */
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 26px;
}
QLineEdit:focus {
    border-color: #89b4fa;
}

/* ── GroupBox ──────────────────────────────────────────────────── */
QGroupBox {
    color: #89b4fa;
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}

/* ── Scrollbar ─────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #181825;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 5px;
    min-width: 20px;
}

/* ── Dock ──────────────────────────────────────────────────────── */
QDockWidget {
    color: #cdd6f4;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}
QDockWidget::title {
    background-color: #181825;
    padding: 4px 8px;
    font-weight: bold;
    border-bottom: 1px solid #45475a;
}

/* ── Splitter ──────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #45475a;
    width: 3px;
    height: 3px;
}
QSplitter::handle:hover {
    background-color: #89b4fa;
}

/* ── Status bar ────────────────────────────────────────────────── */
QStatusBar {
    background-color: #181825;
    color: #6c7086;
    border-top: 1px solid #45475a;
}

/* ── Label ─────────────────────────────────────────────────────── */
QLabel {
    color: #cdd6f4;
}
QLabel#labelEC50 {
    color: #a6e3a1;
    font-size: 20px;
    font-weight: bold;
}
QLabel#labelTitle {
    color: #89b4fa;
    font-size: 15px;
    font-weight: bold;
}
QLabel#labelSubtitle {
    color: #6c7086;
    font-size: 11px;
}

/* ── TextEdit / PlainText ──────────────────────────────────────── */
QTextEdit, QPlainTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
}

/* ── Frame ─────────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #45475a;
}

/* ── Tooltip ───────────────────────────────────────────────────── */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
}
"""

LIGHT_STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #e6e9ef;
    color: #4c4f69;
}
QMenuBar::item:selected { background-color: #dce0e8; }
QMenu { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #bcc0cc; }
QMenu::item:selected { background-color: #dce0e8; }
QTabWidget::pane { border: 1px solid #bcc0cc; background-color: #eff1f5; }
QTabBar::tab { background-color: #e6e9ef; color: #6c6f85; padding: 6px 16px; }
QTabBar::tab:selected { background-color: #dce0e8; color: #4c4f69; border-bottom: 2px solid #1e66f5; }
QTableWidget { background-color: #e6e9ef; color: #4c4f69; gridline-color: #bcc0cc; border: 1px solid #bcc0cc; }
QHeaderView::section { background-color: #dce0e8; color: #1e66f5; padding: 6px; border: none; font-weight: bold; }
QListWidget { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #bcc0cc; }
QListWidget::item:selected { background-color: #bcc0cc; }
QPushButton { background-color: #dce0e8; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background-color: #bcc0cc; }
QPushButton#btnFit { background-color: #1e66f5; color: #fff; font-weight: bold; font-size: 14px; border: none; }
QPushButton#btnFitAll { background-color: #40a02b; color: #fff; font-weight: bold; border: none; }
QComboBox { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; padding: 4px 8px; }
QComboBox QAbstractItemView { background-color: #e6e9ef; color: #4c4f69; selection-background-color: #bcc0cc; }
QSpinBox, QDoubleSpinBox { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; padding: 4px 8px; }
QCheckBox { color: #4c4f69; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #bcc0cc; border-radius: 3px; background-color: #e6e9ef; }
QCheckBox::indicator:checked { background-color: #1e66f5; border-color: #1e66f5; }
QLineEdit { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; padding: 4px 8px; }
QGroupBox { color: #1e66f5; border: 1px solid #bcc0cc; border-radius: 6px; margin-top: 12px; font-weight: bold; }
QScrollBar:vertical { background: #e6e9ef; width: 10px; } QScrollBar::handle:vertical { background: #bcc0cc; border-radius: 5px; }
QStatusBar { background-color: #e6e9ef; color: #6c6f85; }
QLabel#labelEC50 { color: #40a02b; font-size: 20px; font-weight: bold; }
QLabel#labelTitle { color: #1e66f5; font-size: 15px; font-weight: bold; }
QToolTip { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #bcc0cc; }
"""
