"""Configuration de l'utilisateur : un fichier JSON dans le dossier de configuration de l'OS.

Rien n'est écrit dans le dossier d'installation. Un fichier absent, abîmé ou incomplet ne bloque
jamais le démarrage : les valeurs invalides retombent sur leur valeur par défaut et un fichier
illisible est mis de côté en `config.json.bak`.

`client_id` est l'identité de la télécommande appairée dans EasyWorship : elle est générée une fois,
puis conservée. La perdre oblige à ré-accepter la télécommande sur le PC EW.
"""

from __future__ import annotations

import contextlib
import ipaddress
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

log = logging.getLogger("ew_to_obs.config")

APP_DIR = "ew_to_obs"
FILE_NAME = "config.json"
CONFIG_VERSION = 1

_HOST = re.compile(r"^[A-Za-z0-9._-]{1,253}$")
_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_QUERY = re.compile(
    r"^[A-Za-z0-9=&%.,_()#:+-]{0,200}$"
)  # réglages de la page, sans espace ni guillemet


def new_client_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Config:
    version: int = CONFIG_VERSION
    ew_host: str = ""  # nom (ou IP) du PC EasyWorship
    last_ip: str = ""  # dernière IPv4 qui a fonctionné, tentée en premier
    client_id: str = field(default_factory=new_client_id)
    device_name: str = "EasyWorship vers OBS"  # nom montré à l'opérateur dans EW
    web_port: int = 8000
    web_bind: str = "127.0.0.1"
    lost_grace_seconds: float = 2.0
    obs_query: str = "lines=4"  # réglages de la page ajoutés à l'adresse donnée à OBS
    serve: bool = False  # mode sans fenêtre : servir la page sans avoir à passer --serve
    log_level: int = 1  # journal sur stderr en mode sans fenêtre : 0 erreurs … 3 détails


def default_config_dir(env: dict | None = None, platform: str | None = None) -> Path:
    """Dossier de configuration de l'utilisateur, selon l'OS (ou `EW_TO_OBS_CONFIG_DIR`)."""
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    if env.get("EW_TO_OBS_CONFIG_DIR"):
        return Path(env["EW_TO_OBS_CONFIG_DIR"])
    home = Path(env.get("HOME") or env.get("USERPROFILE") or Path.home())
    if platform == "win32":
        return Path(env.get("APPDATA") or home / "AppData" / "Roaming") / APP_DIR
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_DIR
    return Path(env.get("XDG_CONFIG_HOME") or home / ".config") / APP_DIR


def valid_host(value: object) -> bool:
    return isinstance(value, str) and bool(_HOST.match(value.strip()))


def valid_query(value: object) -> bool:
    return isinstance(value, str) and bool(_QUERY.match(value))


def _number(value: object, low: float, high: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if low <= value <= high else None


def _ip(value: object, versions: tuple[int, ...]) -> str | None:
    try:
        address = ipaddress.ip_address(str(value))
    except ValueError:
        return None
    return str(address) if address.version in versions else None


def clean(raw: dict) -> tuple[Config, list[str]]:
    """Config issue d'un JSON : chaque champ invalide reprend sa valeur par défaut."""
    config = Config()
    warnings: list[str] = []

    def reject(name: str, value: object) -> None:
        warnings.append("%s = %r ignoré (invalide), valeur par défaut conservée" % (name, value))

    if "ew_host" in raw:
        value = raw["ew_host"]
        if isinstance(value, str) and (value.strip() == "" or _HOST.match(value.strip())):
            config.ew_host = value.strip()
        else:
            reject("ew_host", value)
    if "last_ip" in raw:
        value = raw["last_ip"]
        if value == "" or _ip(value, (4,)):
            config.last_ip = value
        else:
            reject("last_ip", value)
    if "client_id" in raw:
        value = raw["client_id"]
        if isinstance(value, str) and _ID.match(value):
            config.client_id = value
        else:
            reject("client_id", value)
            warnings.append(
                "un nouveau client_id est généré : la télécommande sera à ré-accepter dans EW"
            )
    if "device_name" in raw:
        value = raw["device_name"]
        if isinstance(value, str) and 1 <= len(value.strip()) <= 40:
            config.device_name = value.strip()
        else:
            reject("device_name", value)
    if "web_port" in raw:
        port = _number(raw["web_port"], 1, 65535)
        if port is not None and float(port).is_integer():
            config.web_port = int(port)
        else:
            reject("web_port", raw["web_port"])
    if "web_bind" in raw:
        value = raw["web_bind"]
        if value == "localhost" or _ip(value, (4, 6)):
            config.web_bind = value
        else:
            reject("web_bind", value)
    if "lost_grace_seconds" in raw:
        grace = _number(raw["lost_grace_seconds"], 0, 60)
        if grace is not None:
            config.lost_grace_seconds = grace
        else:
            reject("lost_grace_seconds", raw["lost_grace_seconds"])
    if "obs_query" in raw:
        value = raw["obs_query"]
        if valid_query(value):
            config.obs_query = value
        else:
            reject("obs_query", value)
    if "serve" in raw:
        if isinstance(raw["serve"], bool):
            config.serve = raw["serve"]
        else:
            reject("serve", raw["serve"])
    if "log_level" in raw:
        level = raw["log_level"]
        if isinstance(level, int) and not isinstance(level, bool) and 0 <= level <= 3:
            config.log_level = level
        else:
            reject("log_level", level)
    version = raw.get("version", CONFIG_VERSION)
    if isinstance(version, int) and version > CONFIG_VERSION:
        warnings.append(
            "config écrite par une version plus récente (%r) : champs inconnus ignorés" % version
        )
    return config, warnings


class ConfigStore:
    """Lecture et écriture de `config.json`. `status` : "ok", "missing" ou "corrupt"."""

    def __init__(self, directory: Path | str | None = None) -> None:
        self.directory = Path(directory) if directory else default_config_dir()
        self.path = self.directory / FILE_NAME
        self.config = Config()
        self.status = "missing"

    def load(self) -> Config:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.config, self.status = Config(), "missing"
            return self.config
        except OSError as exc:
            log.warning("config illisible (%s) : valeurs par défaut", exc)
            self.config, self.status = Config(), "corrupt"
            return self.config
        try:
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise ValueError("le fichier ne contient pas un objet JSON")
        except ValueError as exc:
            self._set_aside(exc)
            self.config, self.status = Config(), "corrupt"
            return self.config
        self.config, warnings = clean(raw)
        for warning in warnings:
            log.warning("config : %s", warning)
        self.status = "ok"
        return self.config

    def _set_aside(self, reason: Exception) -> None:
        backup = self.path.with_name(FILE_NAME + ".bak")
        with contextlib.suppress(OSError):
            os.replace(self.path, backup)
        log.warning(
            "config illisible (%s) : mise de côté dans %s, valeurs par défaut. "
            "Un nouveau client_id est généré : la télécommande sera à ré-accepter dans EW.",
            reason,
            backup,
        )

    def save(self) -> bool:
        """Écriture atomique ; ne lève jamais (dossier en lecture seule, disque plein…)."""
        data = json.dumps(asdict(self.config), indent=2, ensure_ascii=False) + "\n"
        temporary = self.path.with_name(FILE_NAME + ".tmp")
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            temporary.write_text(data, encoding="utf-8")
            with contextlib.suppress(OSError):
                os.chmod(temporary, 0o600)  # l'identité d'appairage n'est pas à partager
            os.replace(temporary, self.path)
        except OSError as exc:
            log.warning("config non enregistrée dans %s : %s", self.path, exc)
            with contextlib.suppress(OSError):
                temporary.unlink()
            return False
        self.status = "ok"
        return True

    def update(self, **values: object) -> bool:
        """Modifie des champs et enregistre seulement si quelque chose a changé (ou si le fichier
        n'existe pas encore)."""
        known = {f.name for f in fields(Config)}
        changed = self.status != "ok"
        for name, value in values.items():
            if name not in known:
                raise KeyError(name)
            if getattr(self.config, name) != value:
                setattr(self.config, name, value)
                changed = True
        return self.save() if changed else True
