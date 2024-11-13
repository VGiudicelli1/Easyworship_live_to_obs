###################################################################################################
##  MACOS APP BUILDER                                                                            ##
##  -------------------------------------------------------------------------------------------  ##
##  to execute: pip install -r requirements.txt && python app.py                                 ##
##  to build: pyinstaller -F --paths envir/lib/python3.8/site-packages src/main.py --clean       ##
##  see envir/readme.md for more                                                                 ##
###################################################################################################

###################################################################################################
##  mise à jour du chemin d'accès                                                                ##
###################################################################################################
import os, sys
from datetime import datetime
from constants import *

if getattr(sys, "frozen", False):
    os.chdir("/".join(sys.executable.split("/")[:-1]))


###################################################################################################
##  ERRORS WRITER                                                                                ##
###################################################################################################
def _write_error_(s, w=sys.stderr.write):
    w(s)
    n = datetime.now()
    date = "%2d:%2d:%2d.%6d    " % (n.hour, n.minute, n.second, n.microsecond)
    with open("err.txt", "a") as f:
        s2 = s.replace("\n", "\n" + len(date) * " ")
        f.write(f"{date}{s2}\n")


sys.stderr.write = _write_error_
with open("err.txt", "w"):
    pass  # efface le fichier
_write_error_("run", w=lambda s: ())
_write_error_(f"python version : {sys.version}\n", w=lambda s: ())
###################################################################################################
##  METADATA                                                                                     ##
###################################################################################################
with open("meta", "w") as meta:
    meta.write(
        f"""EW TO TXT
version : {VERSION}
contact me at vincent.giudicelli@free.fr
source code (open-source) : {GITHUB}
"""
    )

###################################################################################################
##  APP                                                                                          ##
###################################################################################################

import main_imports_pyinstaller
import app

main_imports_pyinstaller

if __name__ == "__main__":
    try:
        main_app = app.App()
        main_app.run()
    finally:
        try:
            main_app._fen.destroy()
        except:
            pass
