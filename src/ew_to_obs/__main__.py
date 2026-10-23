"""Easyworship vers OBS, sans interface.

    python -m ew_to_obs --host NOM_DU_PC_EW --serve    1er lancement : mémorise le PC EW
    python -m ew_to_obs --serve                        lancements suivants : plus rien à saisir

Sans --serve, affiche une ligne JSON à chaque changement de diapo. La configuration (PC EW, dernière
IP, identité de la télécommande) est enregistrée dans le dossier de configuration de l'utilisateur.
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
from .logs import setup_logging
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
    parser.add_argument("--headless", action="store_true", help="(par défaut) sans interface")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def resolve(args: argparse.Namespace, store: ConfigStore) -> Settings | None:
    """Fusionne la ligne de commande et la configuration, et mémorise ce qui doit l'être.

    Mémorisés : le PC EW, l'identité et le nom de la télécommande. Les autres options ne valent que
    pour ce lancement (leurs valeurs durables se règlent dans le fichier de configuration)."""
    config = store.config
    host = args.host or config.ew_host
    if not host:
        return None
    changes: dict[str, object] = {}
    if args.host and args.host != config.ew_host:
        changes.update(ew_host=args.host, last_ip="")  # la dernière IP était celle de l'ancien PC
    if args.client_id and args.client_id != config.client_id:
        changes["client_id"] = args.client_id
    if args.device_name and args.device_name != config.device_name:
        changes["device_name"] = args.device_name
    store.update(**changes)  # écrit aussi le fichier au premier lancement (identité générée)
    return Settings(
        host=host,
        port=args.port,
        client_id=config.client_id,
        device_name=config.device_name,
        grace=args.grace if args.grace is not None else config.lost_grace_seconds,
        serve=args.serve,
        web_bind=args.web_bind or config.web_bind,
        web_port=args.web_port if args.web_port is not None else config.web_port,
        verbose=args.verbose,
    )


def _print_state(state: LiveState) -> None:
    print(
        json.dumps({"visible": state.visible, "text": state.text}, ensure_ascii=False), flush=True
    )


def _print_status(status: ConnectionStatus, detail: str) -> None:
    print("# %s %s" % (status.value, detail), file=sys.stderr, flush=True)


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
        on_status=_print_status,
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
        print("# OBS : Source navigateur → %s" % server.url, file=sys.stderr, flush=True)
    try:
        await client.run()
    finally:
        if server is not None:
            await server.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ConfigStore(args.config_dir)
    if args.show_config:  # lecture seule : ni journal ni écriture
        store.load()
        print("# %s (%s)" % (store.path, store.status))
        print(json.dumps(asdict(store.config), indent=2, ensure_ascii=False))
        return 0
    log_path = setup_logging(
        store.directory, args.verbose
    )  # avant la lecture : ses avertissements y figurent
    store.load()
    settings = resolve(args, store)
    if settings is None:
        print(
            "Indiquez le PC EasyWorship une première fois :\n"
            "  python -m ew_to_obs --host NOM_DU_PC --serve\n"
            "(il sera mémorisé dans %s)" % store.path,
            file=sys.stderr,
        )
        return 2
    log.info("démarrage : PC EW %s, configuration %s", settings.host, store.path)
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
