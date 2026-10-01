from pathlib import Path
import tkinter as tk


LOGO_PATH = Path(__file__).resolve().parent / "icons" / "logo.ico"


def set_window_icon(window) -> None:
	if not LOGO_PATH.is_file():
		return
	try:
		window.iconbitmap(default=str(LOGO_PATH))
	except tk.TclError:
		pass