"""Capture only this app's actual window, not the surrounding desktop."""
from pathlib import Path
import sys,ctypes
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"src"))
from window_capture import capture_owned_window
import tkinter as tk
from zhiyeteam.store import NoteStore
from zhiyeteam.demo import seed_demo
from zhiyeteam.ui import NotebookApp

ROOT=Path(__file__).resolve().parent.parent
if sys.platform=="win32":ctypes.windll.user32.SetProcessDPIAware()
data=ROOT/"runtime"/"capture-demo";data.mkdir(parents=True,exist_ok=True)
store=NoteStore(data/"notes.db");seed_demo(store)
root=tk.Tk();app=NotebookApp(root,store,data,True)
shots=ROOT/"reports"/"screenshots";shots.mkdir(parents=True,exist_ok=True)
def capture():
    root.update_idletasks()
    capture_owned_window(root,shots/"desktop.png")
root.after(600,lambda:app.smoke(ROOT/"reports/gui_smoke.json"))
root.after(1500,capture);root.mainloop()
