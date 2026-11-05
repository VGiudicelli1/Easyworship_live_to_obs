"""Journal de l'application : fichier tournant dans le dossier de configuration.

Le texte des diapos n'est jamais écrit dans le journal (seulement les connexions, les états et les
erreurs), pour pouvoir le joindre à un rapport de recette sans rien divulguer.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_NAME = "ew_to_obs.log"
FORMAT = "%(asctime)s %(levelname)-7s %(name)s : %(message)s"


# --loglevel : 0 erreurs seulement, 1 avertissements, 2 informations (connexions, états), 3 détails
LEVELS = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}


def setup_logging(
    directory: Path, verbose: bool = False, console_level: int | None = None
) -> Path | None:
    """Journal INFO dans `directory/ew_to_obs.log` (1 Mo × 3) ; console WARNING (DEBUG si verbose,
    ou le niveau `console_level` 0 à 3 de `--loglevel`, qui prime).

    Renvoie le chemin du fichier, ou None s'il est impossible de l'ouvrir (on continue sans)."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        if getattr(handler, "_ew_to_obs", False):
            root.removeHandler(handler)
    console = logging.StreamHandler()
    if console_level is not None:
        console.setLevel(LEVELS[console_level])
    else:
        console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter(FORMAT))
    console._ew_to_obs = True  # type: ignore[attr-defined]
    root.addHandler(console)
    path = Path(directory) / LOG_NAME
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    except OSError as exc:
        logging.getLogger("ew_to_obs").warning("journal indisponible (%s)", exc)
        return None
    handler.setLevel(logging.DEBUG if verbose or console_level == 3 else logging.INFO)
    handler.setFormatter(logging.Formatter(FORMAT))
    handler._ew_to_obs = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    return path
