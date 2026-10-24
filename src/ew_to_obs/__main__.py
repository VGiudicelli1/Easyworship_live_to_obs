"""Easyworship vers OBS.

    python -m ew_to_obs                                ouvre la fenêtre (mode normal)
    python -m ew_to_obs --headless --host NOM --serve  sans fenêtre, 1er lancement
    python -m ew_to_obs --headless --serve             sans fenêtre, ensuite : rien à saisir
    python -m ew_to_obs --ci --host NOM --loglevel 2 2>> ew.log   service en arrière-plan

Sans fenêtre et sans --serve, affiche une ligne JSON à chaque changement de diapo. La configuration
(PC EW, dernière IP, identité de la télécommande) est enregistrée dans le dossier de configuration
de l'utilisateur.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict, dataclass

from .client import ConnectionStatus, EwClient
from .config import ConfigStore
from .live import LiveState
from .logs import LEVELS, setup_logging
from .web import StateHub, WebServer

log = logging.getLogger("ew_to_obs")


@dataclass
class Settings:
    host: str
    port: int | None
    client_id: str
    device_name: str
    grace: float
    serve: bool
    web_bind: str
    web_port: int
    verbose: bool
    ci: bool = False  # mode service : l'état de connexion passe par le journal (--loglevel)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ew_to_obs", description=__doc__.splitlines()[0])
    parser.add_argument("--host", help="nom ou IPv4 du PC EasyWorship (mémorisé)")
    parser.add_argument(
        "--client-id", help="identité de la télécommande (mémorisée ; à changer rarement)"
    )
    parser.add_argument("--device-name", help="nom de la télécommande montré dans EW (mémorisé)")
    parser.add_argument(
        "--port", type=int, help="port TCP de la télécommande (diagnostic ; sinon découvert)"
    )
    parser.add_argument(
        "--grace", type=float, help="délai de grâce (s) avant de masquer (config : 2)"
    )
    parser.add_argument("--serve", action="store_true", help="servir la page web pour OBS")
    parser.add_argument("--web-port", type=int, help="port du serveur web (config : 8000)")
    parser.add_argument(
        "--web-bind", help="adresse d'écoute (config : 127.0.0.1 ; 0.0.0.0 = réseau local)"
    )
    parser.add_argument(
        "--config-dir", help="dossier de configuration et de journal (sinon celui de l'OS)"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="affiche la configuration et quitte"
    )
    parser.add_argument(
        "--headless", action="store_true", help="sans fenêtre (sinon : la fenêtre s'ouvre)"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="mode service, sans fenêtre : équivaut à --headless --serve, journal sur stderr",
    )
    parser.add_argument(
        "--loglevel",
        type=int,
        choices=sorted(LEVELS),
        help="détail du journal sur stderr : 0 erreurs, 1 avertissements, 2 infos, 3 détails "
        "(--ci : 2 par défaut)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def remember(args: argparse.Namespace, store: ConfigStore) -> None:
    """Mémorise ce que la ligne de commande fixe durablement : le PC EW, l'identité et le nom de la
    télécommande. Écrit aussi le fichier au premier lancement (l'identité générée doit survivre)."""
    config = store.config
    changes: dict[str, object] = {}
    if args.host and args.host != config.ew_host:
        changes.update(ew_host=args.host, last_ip="")  # la dernière IP était celle de l'ancien PC
    if args.client_id and args.client_id != config.client_id:
        changes["client_id"] = args.client_id
    if args.device_name and args.device_name != config.device_name:
        changes["device_name"] = args.device_name
    store.update(**changes)


def resolve(args: argparse.Namespace, store: ConfigStore) -> Settings | None:
    """Fusionne la ligne de commande et la configuration (mode sans fenêtre).

    Les options autres que le PC EW, l'identité et le nom ne valent que pour ce lancement (leurs
    valeurs durables se règlent dans le fichier de configuration). None sans PC EW connu."""
    if not (args.host or store.config.ew_host):
        return None
    remember(args, store)
    config = store.config
    return Settings(
        host=args.host or config.ew_host,
        port=args.port,
        client_id=config.client_id,
        device_name=config.device_name,
        grace=args.grace if args.grace is not None else config.lost_grace_seconds,
        serve=args.serve or args.ci,
        web_bind=args.web_bind or config.web_bind,
        web_port=args.web_port if args.web_port is not None else config.web_port,
        verbose=args.verbose,
        ci=args.ci,
    )


def _print_state(state: LiveState) -> None:
    print(
        json.dumps({"visible": state.visible, "text": state.text}, ensure_ascii=False), flush=True
    )


def _print_status(status: ConnectionStatus, detail: str) -> None:
    print("# %s %s" % (status.value, detail), file=sys.stderr, flush=True)


def _log_status(status: ConnectionStatus, detail: str) -> None:
    log.info("connexion : %s %s", status.value, detail)


async def run(settings: Settings, store: ConfigStore) -> int:
    hub = StateHub()
    server = WebServer(hub, settings.web_bind, settings.web_port) if settings.serve else None

    def on_state(state: LiveState) -> None:
        hub.publish(state)
        if server is None or settings.verbose:
            _print_state(state)

    client = EwClient(
        settings.host,
        settings.client_id,
        settings.device_name,
        port=settings.port,
        last_ip=store.config.last_ip or None,
        grace_seconds=settings.grace,
        on_state=on_state,
        on_status=_log_status if settings.ci else _print_status,
        on_ip=lambda ip: store.update(last_ip=ip),  # mémorise la dernière IP qui a fonctionné
    )
    if server is not None:
        try:
            await server.start()
        except OSError as exc:
            message = (
                "Impossible d'ouvrir le serveur web sur %s:%d (%s).\n"
                "Le port est probablement déjà utilisé : essayez --web-port %d."
                % (settings.web_bind, settings.web_port, exc, settings.web_port + 1)
            )
            log.error(message.replace("\n", " "))
            print(message, file=sys.stderr)
            return 2
        if settings.ci:
            log.info("page pour OBS : %s", server.url)
        else:
            print("# OBS : Source navigateur → %s" % server.url, file=sys.stderr, flush=True)
    try:
        await client.run()
    finally:
        if server is not None:
            await server.stop()
    return 0


def _main_window(args: argparse.Namespace, store: ConfigStore) -> int:
    """Mode normal : la fenêtre. Demande tkinter et un écran ; sinon explique comment faire sans."""
    try:
        import tkinter

        from .service import Service
        from .ui import run_ui
    except ImportError as exc:
        print(
            "La fenêtre demande tkinter (%s).\n"
            "macOS : utilisez le Python de python.org, ou `brew install python-tk`.\n"
            "Linux : `sudo apt install python3-tk`.\n"
            "Sans fenêtre : python -m ew_to_obs --headless --host NOM_DU_PC --serve" % exc,
            file=sys.stderr,
        )
        return 3
    remember(args, store)  # --host, --client-id, --device-name restent mémorisés
    log.info("démarrage de la fenêtre, configuration %s", store.path)
    try:
        return run_ui(Service(store, ew_port=args.port))
    except tkinter.TclError as exc:
        print(
            "Impossible d'ouvrir la fenêtre (%s).\n"
            "Sans fenêtre : python -m ew_to_obs --headless --host NOM_DU_PC --serve" % exc,
            file=sys.stderr,
        )
        return 3
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ConfigStore(args.config_dir)
    if args.show_config:  # lecture seule : ni journal ni écriture
        store.load()
        print("# %s (%s)" % (store.path, store.status))
        print(json.dumps(asdict(store.config), indent=2, ensure_ascii=False))
        return 0
    # le journal s'ouvre avant la lecture de la config : ses avertissements y figurent
    level = args.loglevel if args.loglevel is not None else (2 if args.ci else None)
    log_path = setup_logging(store.directory, args.verbose, level)
    store.load()
    if not (args.headless or args.ci):
        return _main_window(args, store)
    settings = resolve(args, store)
    if settings is None:
        print(
            "Indiquez le PC EasyWorship une première fois :\n"
            "  python -m ew_to_obs --ci --host NOM_DU_PC\n"
            "(il sera mémorisé dans %s)" % store.path,
            file=sys.stderr,
        )
        return 2
    log.info("démarrage : PC EW %s, configuration %s", settings.host, store.path)
    if not settings.ci:
        print(
            "# configuration : %s ; journal : %s" % (store.path, log_path or "indisponible"),
            file=sys.stderr,
        )
    try:
        return asyncio.run(run(settings, store))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
