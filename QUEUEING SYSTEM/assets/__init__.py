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


def center_window(window: tk.Misc) -> None:
	window.update_idletasks()
	width = window.winfo_width()
	height = window.winfo_height()
	x = max((window.winfo_screenwidth() - width) // 2, 0)
	y = max((window.winfo_screenheight() - height) // 2, 0)
	window.geometry(f"{width}x{height}+{x}+{y}")