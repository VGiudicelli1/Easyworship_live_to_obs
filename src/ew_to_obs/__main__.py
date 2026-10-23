"""Mode sans interface : affiche chaque changement de diapo en direct (une ligne JSON par état).

python -m ew_to_obs --host NOM_OU_IP_DU_PC_EW
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid

from .client import ConnectionStatus, EwClient
from .live import LiveState

# Identité de la V1, déjà appairée dans EW ; la génération d'un identifiant par installation viendra
# avec la configuration (étape 3 du plan).
V1_CLIENT_ID = "a164e834-fc66-4cff-8e47-aa904ee9e62b"


def _print_state(state: LiveState) -> None:
    print(
        json.dumps({"visible": state.visible, "text": state.text}, ensure_ascii=False), flush=True
    )


def _print_status(status: ConnectionStatus, detail: str) -> None:
    print("# %s %s" % (status.value, detail), file=sys.stderr, flush=True)


async def _run(args: argparse.Namespace) -> None:
    client = EwClient(
        args.host,
        args.client_id,
        args.device_name,
        port=args.port,
        grace_seconds=args.grace,
        on_state=_print_state,
        on_status=_print_status,
    )
    await client.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ew_to_obs", description=__doc__.splitlines()[0])
    parser.add_argument("--host", required=True, help="nom ou adresse IPv4 du PC EasyWorship")
    parser.add_argument("--port", type=int, help="port TCP de la télécommande (sinon découvert)")
    parser.add_argument("--client-id", default=V1_CLIENT_ID, help="uid de la télécommande")
    parser.add_argument("--device-name", default="ew to obs")
    parser.add_argument(
        "--grace", type=float, default=2.0, help="délai de grâce (s) avant de masquer"
    )
    parser.add_argument("--headless", action="store_true", help="(par défaut) sans interface")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    if not args.client_id:
        args.client_id = str(uuid.uuid4())
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
