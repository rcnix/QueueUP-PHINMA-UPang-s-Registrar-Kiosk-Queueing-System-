from pathlib import Path
import tkinter as tk


LOGO_PATH = Path(__file__).resolve().parent / "icons" / "logo.ico"


def format_counter_label(number: int, name: str) -> str:
	counter = f"COUNTER {number}"
	return counter if name.strip().casefold() == counter.casefold() else f"{counter} - {name}"


def set_window_icon(window) -> None:
	if not LOGO_PATH.is_file():
		return
	try:
		window.iconbitmap(default=str(LOGO_PATH))
	except tk.TclError:
		pass


def center_window(window: tk.Misc) -> None:
	window.update_idletasks()
	width = window._current_width
	height = window._current_height
	x = max((window.winfo_screenwidth() - width) // 2, 0)
	y = max((window.winfo_screenheight() - height) // 2, 0)
	window.geometry(f"+{x}+{y}")


def enable_tab_auto_hide_on_scroll(tabview: tk.Misc) -> None:
	root = tabview.winfo_toplevel()
	state = getattr(root, "_tab_scroll_state", None)
	if state is None:
		state = {"tabviews": [], "restore_job": None}
		root._tab_scroll_state = state

		def show_tabs() -> None:
			for registered_tabview in state["tabviews"]:
				try:
					registered_tabview._segmented_button.grid()
				except tk.TclError:
					pass
			state["restore_job"] = None

		def hide_tabs(_event=None) -> None:
			for registered_tabview in state["tabviews"]:
				try:
					registered_tabview._segmented_button.grid_remove()
				except tk.TclError:
					pass
			if state["restore_job"] is not None:
				try:
					root.after_cancel(state["restore_job"])
				except tk.TclError:
					pass
			state["restore_job"] = root.after(1000, show_tabs)

		root._tab_scroll_hide = hide_tabs
		root.bind_all("<MouseWheel>", hide_tabs, add="+")
		root.bind_all("<Button-4>", hide_tabs, add="+")
		root.bind_all("<Button-5>", hide_tabs, add="+")
	else:
		hide_tabs = root._tab_scroll_hide
		state = root._tab_scroll_state

	if tabview not in state["tabviews"]:
		state["tabviews"].append(tabview)