"""Internet's Dream — Linux desktop client (PyQt6).

Thin client for `dreamcore serve` (default http://127.0.0.1:8765).
Material-You-inspired dark theme. Run:  python -m dream_desktop
"""

from __future__ import annotations

import json
import sys
import urllib.request

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton,
    QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget, QSystemTrayIcon,
)

API = "http://127.0.0.1:8765"

STYLESHEET = """
QMainWindow, QWidget { background: #10131a; color: #e6e1e5; font-family: "Segoe UI", "Noto Sans", sans-serif; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 10px 18px; background: #1d1b20; color: #cac4d0; border-radius: 12px 12px 0 0; margin-right: 4px; }
QTabBar::tab:selected { background: #4a4458; color: #fff; }
QLineEdit, QPlainTextEdit {
    background: #1d1b20; border: 1px solid #49454f; border-radius: 12px;
    padding: 10px 12px; font-size: 14px; color: #e6e1e5;
}
QLineEdit:focus { border-color: #d0bcff; }
QPushButton {
    background: #d0bcff; color: #381e72; border: none; border-radius: 999px;
    padding: 10px 22px; font-weight: 600;
}
QPushButton:hover { background: #eaddff; }
QPushButton.secondary { background: #4a4458; color: #e8def8; }
QLabel#title { font-size: 26px; font-weight: 600; }
QLabel.muted { color: #938f99; font-size: 13px; }
QLabel.card {
    background: #211f26; border-radius: 16px; padding: 14px;
}
"""


def api_get(path: str) -> dict | list:
    with urllib.request.urlopen(API + path, timeout=5) as r:
        return json.loads(r.read())


def api_post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


class DreamWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Internet's Dream")
        self.resize(980, 680)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Internet's Dream")
        title.setObjectName("title")
        sub = QLabel("Universal Contextual Memory · local encrypted store · "
                     f"backend {API}")
        sub.setObjectName("muted")
        root.addWidget(title)
        root.addWidget(sub)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._dashboard_tab(), "Dashboard")
        self.tabs.addTab(self._search_tab(), "Search")
        self.tabs.addTab(self._ask_tab(), "Ask")
        self.tabs.addTab(self._settings_tab(), "Settings")
        root.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        # system tray
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Internet's Dream")
        self.tray.show()

        QTimer.singleShot(300, self.refresh_dashboard)

    # -- tabs ---------------------------------------------------------

    def _dashboard_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.dash_stats = QLabel("connecting…")
        self.dash_stats.setObjectName("muted")
        self.dash_recent = QPlainTextEdit()
        self.dash_recent.setReadOnly(True)
        lay.addWidget(self.dash_stats)
        lay.addWidget(self.dash_recent, 1)
        return w

    def refresh_dashboard(self):
        try:
            s = api_get("/stats")
            self.dash_stats.setText(
                f"{s.get('total', 0)} memories · "
                + ", ".join(f"{k}: {v}" for k, v in (s.get("by_source") or {}).items()))
        except Exception as e:
            self.dash_stats.setText(f"backend offline ({e}) — run: dream serve")
        try:
            hits = api_get("/search?q=the&limit=8")
            self.dash_recent.setPlainText(
                "\n\n".join(f"• {h.get('title','?')} — {(h.get('snippet') or '')[:110]}"
                            for h in hits))
        except Exception:
            self.dash_recent.setPlainText("")

    def _search_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search your memories…")
        btn = QPushButton("Search")
        btn.clicked.connect(self.do_search)
        self.search_input.returnPressed.connect(self.do_search)
        row.addWidget(self.search_input, 1)
        row.addWidget(btn)
        lay.addLayout(row)
        self.search_out = QPlainTextEdit()
        self.search_out.setReadOnly(True)
        lay.addWidget(self.search_out, 1)
        return w

    def do_search(self):
        q = self.search_input.text().strip()
        if not q:
            return
        try:
            hits = api_get("/search?q=" + urllib.parse.quote(q) + "&limit=20")
            self.search_out.setPlainText("\n\n".join(
                f"[{h.get('score', 0):.2f}] {h.get('title','?')} · {h.get('sender') or '?'}\n"
                f"  {(h.get('snippet') or '')[:200]}"
                for h in hits) or "no results")
        except Exception as e:
            self.search_out.setPlainText(f"backend offline: {e}")

    def _ask_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.ask_input = QLineEdit()
        self.ask_input.setPlaceholderText("Ask your second brain…")
        btn = QPushButton("Ask")
        btn.clicked.connect(self.do_ask)
        self.ask_input.returnPressed.connect(self.do_ask)
        row = QHBoxLayout()
        row.addWidget(self.ask_input, 1)
        row.addWidget(btn)
        lay.addLayout(row)
        self.ask_out = QPlainTextEdit()
        self.ask_out.setReadOnly(True)
        lay.addWidget(self.ask_out, 1)
        return w

    def do_ask(self):
        q = self.ask_input.text().strip()
        if not q:
            return
        self.ask_out.setPlainText("thinking…")
        try:
            r = api_post("/ask", {"question": q})
            self.ask_out.setPlainText(r.get("answer", ""))
        except Exception as e:
            self.ask_out.setPlainText(f"backend offline: {e}")

    def _settings_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lbl = QLabel(
            "Configure the LLM gateway on the backend:\n\n"
            "  dream config --provider openai-compatible \\\n"
            "    --base-url https://api.openai.com/v1 \\\n"
            "    --api-key sk-... --model gpt-4o-mini\n\n"
            "All data stays on this machine. AES-256-GCM at rest, zero telemetry.")
        lbl.setWordWrap(True)
        btn = QPushButton("Refresh dashboard")
        btn.setObjectName("secondary")
        btn.clicked.connect(self.refresh_dashboard)
        lay.addWidget(lbl)
        lay.addWidget(btn)
        lay.addStretch(1)
        return w


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DreamWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
