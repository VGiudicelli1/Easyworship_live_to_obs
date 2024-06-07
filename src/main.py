import tkinter as tk

fen = tk.Tk()
fen.title('Easyworkship to textfile')

label = tk.Label(fen)
label.pack()

label.config(text='status: ARRET')

btn_start = tk.Button(fen, text='START')
btn_start.pack()

btn_stop = tk.Button(fen, text='STOP')
btn_stop.pack()

def start(event):
    print('start')

btn_start.bind("<Button>", start)
fen.mainloop()