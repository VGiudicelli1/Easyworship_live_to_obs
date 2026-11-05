"""Fenêtre de l'application (Tkinter) : une seule page, pas de menus.

Elle ne fait que lire l'instantané du service à intervalle régulier et lui transmettre les
réglages ; tout le travail réseau se fait dans le thread du service.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .config import valid_host, valid_query
from .logs import LOG_NAME
from .service import Service
from .status_text import browsers_text, describe, preview_text

REFRESH_MS = 250
COLORS = {"ok": "#1a7f37", "wait": "#b25e00", "bad": "#c62828", "off": "#777777"}


def open_folder(path: Path) -> None:
    """Ouvre un dossier dans le gestionnaire de fichiers de l'OS."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])  # noqa: S603, S607
    else:
        subprocess.Popen(["xdg-open", str(path)])  # noqa: S603, S607


class App:
    def __init__(self, root: tk.Tk, service: Service) -> None:
        self.root = root
        self.service = service
        config = service.store.config
        root.title("Easyworship vers OBS")
        root.geometry("720x440")  # assez large pour voir toute l'adresse pour OBS
        root.minsize(640, 400)
        root.protocol("WM_DELETE_WINDOW", self.quit)

        self.host_var = tk.StringVar(value=config.ew_host)
        self.port_var = tk.StringVar(value=str(config.web_port))
        self.query_var = tk.StringVar(value=config.obs_query)
        self.status_var = tk.StringVar()
        self.detail_var = tk.StringVar()
        self.banner_var = tk.StringVar()
        self.browsers_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.preview_var = tk.StringVar()
        self.copied_var = tk.StringVar()
        self._form_error = ""
        self._after_id: str | None = None

        frame = ttk.Frame(root, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(frame, text="PC EasyWorship").grid(row=row, column=0, sticky="w", pady=3)
        self.host_entry = ttk.Entry(frame, textvariable=self.host_var)
        self.host_entry.grid(row=row, column=1, sticky="ew", padx=8)
        self.apply_button = ttk.Button(frame, text="Appliquer", command=self.apply)
        self.apply_button.grid(row=row, column=2)
        self.host_entry.bind("<Return>", lambda _event: self.apply())
        row += 1

        ttk.Label(frame, text="État").grid(row=row, column=0, sticky="w", pady=3)
        state_box = ttk.Frame(frame)
        state_box.grid(row=row, column=1, columnspan=2, sticky="w", padx=8)
        self.dot = tk.Label(state_box, text="●", font=("TkDefaultFont", 14))
        self.dot.pack(side="left")
        self.status_label = ttk.Label(state_box, textvariable=self.status_var)
        self.status_label.pack(side="left", padx=6)
        row += 1

        self.detail_label = ttk.Label(
            frame, textvariable=self.detail_var, foreground="#777777", wraplength=640
        )
        self.detail_label.grid(row=row, column=1, columnspan=2, sticky="w", padx=8)
        row += 1

        self.banner_label = tk.Label(
            frame, textvariable=self.banner_var, wraplength=640, justify="left", anchor="w"
        )
        self.banner_label.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(6, 2))
        row += 1

        ttk.Label(frame, text="Navigateurs (OBS)").grid(row=row, column=0, sticky="w", pady=3)
        ttk.Label(frame, textvariable=self.browsers_var).grid(
            row=row, column=1, columnspan=2, sticky="w", padx=8
        )
        row += 1

        ttk.Label(frame, text="Adresse pour OBS").grid(row=row, column=0, sticky="w", pady=3)
        self.url_entry = ttk.Entry(frame, textvariable=self.url_var, state="readonly")
        self.url_entry.grid(row=row, column=1, sticky="ew", padx=8)
        self.copy_button = ttk.Button(frame, text="Copier", command=self.copy_url)
        self.copy_button.grid(row=row, column=2)
        row += 1
        ttk.Label(frame, textvariable=self.copied_var, foreground=COLORS["ok"]).grid(
            row=row, column=1, sticky="w", padx=8
        )
        row += 1

        ttk.Label(frame, text="Réglages de la page").grid(row=row, column=0, sticky="w", pady=3)
        self.query_entry = ttk.Entry(frame, textvariable=self.query_var)
        self.query_entry.grid(row=row, column=1, sticky="ew", padx=8)
        self.query_entry.bind("<Return>", lambda _event: self.apply())
        ttk.Label(frame, text="ex. lines=4&valign=bottom", foreground="#777777").grid(
            row=row, column=2, sticky="w"
        )
        row += 1

        ttk.Label(frame, text="Port de la page").grid(row=row, column=0, sticky="w", pady=3)
        self.port_entry = ttk.Entry(frame, textvariable=self.port_var, width=8)
        self.port_entry.grid(row=row, column=1, sticky="w", padx=8)
        self.port_entry.bind("<Return>", lambda _event: self.apply())
        row += 1

        ttk.Label(frame, text="Aperçu").grid(row=row, column=0, sticky="nw", pady=6)
        self.preview_label = tk.Label(
            frame,
            textvariable=self.preview_var,
            wraplength=560,
            justify="left",
            anchor="nw",
            relief="sunken",
            borderwidth=1,
            padx=6,
            pady=4,
            height=5,
            background="#f4f4f4",
        )
        self.preview_label.grid(row=row, column=1, columnspan=2, sticky="nsew", padx=8, pady=6)
        frame.rowconfigure(row, weight=1)
        row += 1

        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=3, sticky="e", pady=(8, 0))
        self.log_button = ttk.Button(
            buttons, text="Ouvrir le dossier du journal", command=self.open_log
        )
        self.log_button.pack(side="left", padx=6)
        self.quit_button = ttk.Button(buttons, text="Quitter", command=self.quit)
        self.quit_button.pack(side="left")

        self.refresh()

    # ------------------------------------------------------------------ actions
    def apply(self) -> None:
        host = self.host_var.get().strip()
        query = self.query_var.get().strip()
        if not host:
            return self._reject("Saisissez le nom du PC EasyWorship.")
        if not valid_host(host):
            return self._reject(
                "Nom de PC invalide : lettres, chiffres, points et tirets seulement."
            )
        try:
            port = int(self.port_var.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            return self._reject("Port de la page invalide : un nombre entre 1 et 65535.")
        if not valid_query(query):
            return self._reject(
                "Réglages de la page invalides : lettres, chiffres et = & % . , _ ( ) # : + - "
                "seulement."
            )
        self._form_error = ""
        self.copied_var.set("")
        self.service.configure(host, port, query)
        self.refresh()

    def _reject(self, message: str) -> None:
        self._form_error = message
        self.refresh()

    def copy_url(self) -> None:
        url = self.url_var.get()
        if not url:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.root.update()  # laisse le presse-papiers à l'OS même si la fenêtre se ferme
        self.copied_var.set("Adresse copiée")
        self.root.after(2000, lambda: self.copied_var.set(""))

    def open_log(self) -> None:
        directory = self.service.store.directory
        try:
            directory.mkdir(parents=True, exist_ok=True)
            open_folder(directory)
        except OSError as exc:
            self._reject("Impossible d'ouvrir %s : %s (fichier %s)" % (directory, exc, LOG_NAME))

    def quit(self) -> None:
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self.root.destroy()

    # ------------------------------------------------------------------ affichage
    @staticmethod
    def _show(widget: tk.Widget, visible: bool) -> None:
        """Affiche ou masque une ligne de la grille (sans laisser de vide quand elle est vide)."""
        if visible:
            widget.grid()
        else:
            widget.grid_remove()

    def refresh(self) -> None:
        snap = self.service.snapshot()
        view = describe(snap, self.service.store.config.device_name)
        self.status_var.set(view.label)
        self.detail_var.set(view.detail)
        self._show(self.detail_label, bool(view.detail))
        self.dot.configure(foreground=COLORS[view.color])
        banner, is_error = (
            (self._form_error, True) if self._form_error else (view.banner, view.banner_is_error)
        )
        self.banner_var.set(banner)
        self._show(self.banner_label, bool(banner))
        self.banner_label.configure(
            foreground=COLORS["bad"] if is_error else COLORS["wait"],
            font=("TkDefaultFont", 11, "bold"),
        )
        self.browsers_var.set(browsers_text(snap.browsers) if snap.url else "—")
        query = self.query_var.get().strip()
        shown = snap.url + ("?" + query if query and valid_query(query) and snap.url else "")
        self.url_var.set(shown)
        self.copy_button.state(["!disabled"] if shown else ["disabled"])
        self.preview_var.set(preview_text(snap.state) if snap.configured else "")
        self._after_id = self.root.after(REFRESH_MS, self.refresh)


def run_ui(service: Service) -> int:
    root = tk.Tk()
    service.start()
    App(root, service)
    try:
        root.mainloop()
    finally:
        service.stop()
    return 0
