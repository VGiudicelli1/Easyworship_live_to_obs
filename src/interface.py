# interface d'acceuil

from ew_api import EW_API
import tkinter as tk
from constants import Colors
import time
import logger

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg = Colors.background)

        self.ew = None
        
        lbl_chargement = tk.Label(master, text = "Easyworkship to txt\n\nChargement en cours...", bg = Colors.background)
        lbl_chargement.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)


        lbl_ew_title = tk.Label(master, text = "EasyWorkship")
        lbl_ew_title.grid(column=1,columnspan=2,row=1)
        #lbl_ew_title.place(relx=0.1, rely=0.1, relwidth=0.4, relheight=0.1)

        lbl_ew_ip = tk.Label(master, text = "Host ip")
        lbl_ew_ip.grid(column=1,row=2)

        lbl_ew_port = tk.Label(master, text = "Host port")
        lbl_ew_port.grid(column=1,row=3)

        lbl_ew_status = tk.Label(master, text = "Status")
        lbl_ew_port.grid(column=1,row=4)

        btn_ew_start = tk.Button(master, text = "Start")
        btn_ew_start.grid(column=1, columnspan=2, row=5)
        btn_ew_start.bind("<Button>", self.start)

        btn_ew_stop = tk.Button(master, text = "Stop")
        btn_ew_stop.grid(column=1, columnspan=2, row=6)
        btn_ew_stop.bind("<Button>", self.stop)

        btn_quit = tk.Button(master, text = "Quit")
        btn_quit.grid(column=1, columnspan=2, row=7)
        btn_quit.bind("<Button>", self.quit)

        super().place(relx = 0, rely = 0, relwidth = 0)
        super().update()
        super().place_forget()

        lbl_chargement.place_forget()
        lbl_chargement.destroy()

    def quit(self, event = None):
        super().quit()
        self.master.destroy()

    def place(self):
        super().place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        
    def place_forget(self):
        try:
            super().place_forget()
        except tk._tkinter.TclError:
            pass

    def run(self):
        self.place()
        self.mainloop()
        self.place_forget()

    def start(self, event = None):
        if (self.ew != None):
            self.ew.disconnect()
        self.ew = None#EW_API()#logger=logger.LoggerSlideContentToTxt())
        #self.ew.connect()

    def stop(self, event = None):
        if (self.ew != None):
            self.ew.disconnect()
            self.ew = None


if __name__ == "__main__":
    fen = tk.Tk()
    fen.geometry("900x600")

    accueil = App(fen)
    accueil.place()

    accueil.run()

    try:
        fen.destroy()
    except tk._tkinter.TclError:
        pass



