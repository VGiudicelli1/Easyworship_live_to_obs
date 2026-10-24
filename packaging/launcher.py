"""Point d'entrée de l'exécutable PyInstaller (le paquet utilise des imports relatifs)."""

import sys

from ew_to_obs.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
