####################################################################################################
####################################################################################################
####################################################################################################
### mise à jour du chemin d'accès ##################################################################
import os, sys
from datetime import datetime

if getattr(sys, "frozen", False):
    os.chdir("/".join(sys.executable.split("/")[:-1]))

### ajout d'un fichier d'erreurs ###################################################################
def _write_error_(s, w = sys.stderr.write):
    w(s)
    n = datetime.now()
    date = "%2d:%2d:%2d.%6d    " % (n.hour, n.minute, n.second, n.microsecond)
    with open("err.txt", "a") as f:
        s2 = s.replace("\n","\n"+len(date) * " ")
        f.write(f"{date}{s2}\n")
sys.stderr.write = _write_error_
with open("err.txt","w"):pass   # efface le fichier
_write_error_("run\n", w = lambda s:())

### création des métadonnées (fichier contenant entre autre la version du programme) ###############
VERSION = "1.0.0"
with open("meta", "w") as meta:
    meta.write(f"""EW TO TXT
version : {VERSION}
distrib_date : 2024-06-08
contact me at vincent.giudicelli@free.fr
source code (open-source) : https://github.com/VGiudicelli1/Easyworship_live_to_obs.git
""")

## app

import tkinter as tk
import interface


if __name__ == "__main__":
    fen = tk.Tk()
    fen.title(f"EasyWrokship to txt {VERSION}")

    fen.bind_all("<Triple-Shift-Escape>",
                 lambda event:(_write_error_("emergency destroy\n"),
                               fen.destroy()))
    #fen.geometry("900x600")

    try:
        app = interface.App(fen)
        app.run()
    finally:
        try:
            fen.destroy()
        except:
            pass
