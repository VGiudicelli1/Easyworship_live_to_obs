# interface d'acceuil

from ew_api import EW_API
import tkinter as tk
from constants import Colors
import time
import logger
import threading
from storage import Slide

class Params:
    host: tk.StringVar
    port: tk.IntVar
    client_id: tk.StringVar
    out_path: tk.StringVar

    def __init__(self:"Params", master:"tk.Widget|None"=None):
        self.host = tk.StringVar(master=master, value='192.168.0.213')
        self.port = tk.IntVar(master=master, value=5353)
        self.client_id = tk.StringVar(master=master, value='a164e834-fc66-4cff-8e47-aa904ee9e62b')
        self.out_path = tk.StringVar(master=master, value='')

    def load(self:"Params"):
        pass

    def save(self:"Params"):
        pass

class Datas:
    status: tk.StringVar
    current_text: tk.StringVar

    def __init__(self:"Datas", master:"tk.Widget|None"=None):
        self.status = tk.StringVar(master=master, value='No status')
        self.current_text = tk.StringVar(master=master, value='')

class App(tk.Frame):
    ew: "EW_API | None"
    params: Params

    def __init__(self:"App", master:tk.Widget):
        super().__init__(master, bg = Colors.background)

        self.ew = None

        self.params = Params(self)
        self.params.load()

        self.datas = Datas(self)
        
        lbl_chargement = tk.Label(master, text = "Easyworkship to txt\n\nChargement en cours...", bg = Colors.background)
        lbl_chargement.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)


        lbl_ew_title = tk.Label(master, text = "EasyWorkship")
        lbl_ew_title.grid(column=1,columnspan=2,row=1, sticky = "NEWS")
        #lbl_ew_title.place(relx=0.1, rely=0.1, relwidth=0.4, relheight=0.1)

        lbl_ew_ip = tk.Label(master, text = "Host ip")
        lbl_ew_ip.grid(column=1,row=2, sticky = "NEWS")

        inp_ew_host = tk.Entry(master, textvariable=self.params.host)
        inp_ew_host.grid(column=2, row=2, sticky = "NEWS")

        lbl_ew_port = tk.Label(master, text = "Host port")
        lbl_ew_port.grid(column=1, row=3, sticky = "NEWS")

        inp_ew_port = tk.Entry(master, textvariable=self.params.port)
        inp_ew_port.grid(column=2, row=3, sticky = "NEWS")

        lbl_ew_status = tk.Label(master, text="Status")
        lbl_ew_status.grid(column=1,row=4, sticky = "NEWS")

        lbl_ew_status_var = tk.Label(master, textvariable=self.datas.status)
        lbl_ew_status_var.grid(column=2, row=4, sticky = "NEWS")

        btn_ew_start = tk.Button(master, text = "Start", command=self.start)
        btn_ew_start.grid(column=1, columnspan=2, row=5, sticky = "NEWS")
        #btn_ew_start.bind("<Button>", self.start)

        btn_ew_stop = tk.Button(master, text = "Stop", command=self.stop)
        btn_ew_stop.grid(column=1, columnspan=2, row=6, sticky = "NEWS")

        btn_quit = tk.Button(master, text = "Quit", command=self.quit)
        btn_quit.grid(column=1, columnspan=2, row=7, sticky = "NEWS")


        lbl_out_title = tk.Label(master, text = "Output")
        lbl_out_title.grid(column=3,columnspan=2,row=1, sticky = "NEWS")
        
        lbl_out_path = tk.Label(master, text="path")
        lbl_out_path.grid(column=3, row=2, sticky = "NEWS")

        inp_out_path = tk.Entry(master, textvariable=self.params.out_path)
        inp_out_path.grid(column=4, row=2, sticky="NEWS")

        lbl_out_text = tk.Label(master, textvariable=self.datas.current_text)
        lbl_out_text.grid(column=3, row=3, columnspan=2, rowspan=5, sticky="NEWS")

        super().place(relx = 0, rely = 0, relwidth = 0)
        super().update()
        super().place_forget()

        lbl_chargement.place_forget()
        lbl_chargement.destroy()

    def quit(self:"App", event = None):
        super().quit()
        self.master.destroy()

    def place(self:"App"):
        super().place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        
    def place_forget(self:"App"):
        try:
            super().place_forget()
        except tk._tkinter.TclError:
            pass

    def run(self:"App"):
        self.place()
        self.mainloop()
        self.place_forget()

    def start(self:"App", event:"tk.Event|None" = None):
        threading.Thread(target=self._start_body).start()

    def _start_body(self:"App"):
        if (self.ew != None):
            self.ew.disconnect()
            self.ew.removeAllEvents()
        self.ew = EW_API(
            host=self.params.host.get(),
            port=self.params.port.get(),
            client_id=self.params.client_id.get()
        )
        self.datas.status.set('connecting...')
        self.ew.addEventListener("disconnected", lambda e:self.datas.status.set('disconnected'))
        self.ew.addEventListener("error", lambda e:self.datas.status.set('error ' + e))
        self.ew.addEventListener("connected", lambda e:self.datas.status.set('connected'))
        self.ew.addEventListener("current_slide_changed", self.on_current_slide_change)
        self.ew.addEventListener("content_visible", self.on_current_slide_change)
        self.ew.addEventListener("content_unvisible", self.on_current_slide_change)
        self.ew.connect()

    def stop(self:"App", event:"tk.Event|None" = None):
        threading.Thread(target=self._stop_body).start()

    def _stop_body(self:"App"):
        if (self.ew != None):
            self.ew.disconnect()

    def on_current_slide_change(self, slide: "Slide|None"):
        text:str = str(slide) if slide else ''
        self.datas.current_text.set(text)
        try:
            with open(self.params.out_path.get(), 'w') as f:
                f.write(text)
        except:
            print('fail to write in file')

if __name__ == "__main__":
    fen = tk.Tk()
    #fen.geometry("900x600")

    accueil = App(fen)
    accueil.place()

    accueil.run()

    try:
        fen.destroy()
    except tk._tkinter.TclError:
        pass



