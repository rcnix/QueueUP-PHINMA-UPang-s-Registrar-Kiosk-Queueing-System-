# MODULE UTILITIES - ADMIN UI
# Shared helper functions for building responsive layouts and formatting
# counter labels across the QueueUP application.

from collections.abc import Sequence
from pathlib import Path
import tkinter as tk


ICONS_DIR = Path(__file__).resolve().parent / "icons"
LOGO_PATH = ICONS_DIR / "logo.ico"
LOGO_IMAGE_PATH = ICONS_DIR / "logo.png"


def responsive_grid_columns(
	width: int,
	minimum_item_width: int,
	max_columns: int = 3,
) -> int:
	return max(1, min(max_columns, width // minimum_item_width))


def layout_responsive_grid(
	container: tk.Misc,
	items: Sequence[tk.Misc],
	width: int,
	minimum_item_width: int,
	padding: int = 10,
	max_columns: int = 3,
	expand_rows: bool = False,
) -> int:
	columns = responsive_grid_columns(width, minimum_item_width, max_columns)
	if getattr(container, "_responsive_grid_columns", None) == columns:
		return columns

	rows = max(1, (len(items) + columns - 1) // columns)
	previous_columns = getattr(container, "_responsive_grid_max_columns", 0)
	previous_rows = getattr(container, "_responsive_grid_rows", 0)
	for column in range(max(max_columns, previous_columns)):
		active = column < columns
		container.grid_columnconfigure(
			column,
			weight=1 if active else 0,
			uniform="responsive-grid-column" if active else "",
		)
	for row in range(max(rows, previous_rows)):
		active = row < rows
		container.grid_rowconfigure(
			row,
			weight=1 if expand_rows and active else 0,
			uniform="responsive-grid-row" if expand_rows and active else "",
		)
	for index, item in enumerate(items):
		item.grid(
			row=index // columns,
			column=index % columns,
			padx=padding,
			pady=padding,
			sticky="nsew",
		)

	container._responsive_grid_columns = columns
	container._responsive_grid_max_columns = max(max_columns, previous_columns)
	container._responsive_grid_rows = rows
	return columns


def format_counter_label(number: int, name: str) -> str:
	name = name.strip()
	if not name:
		return f"COUNTER {number}"
	if name.casefold() == f"counter {number}".casefold():
		return name
	return f"COUNTER {number} - {name}"


def set_window_icon(window) -> None:
	if not LOGO_PATH.is_file():
		return
	try:
		window.iconbitmap(default=str(LOGO_PATH))
	except tk.TclError:
		pass

def _rounded_logo_image(image, size: int, radius: int):
	from PIL import Image, ImageChops, ImageDraw

	scale = 4
	pixels = size * scale
	image = image.convert("RGBA").resize((pixels, pixels), Image.LANCZOS)
	if radius <= 0:
		return image
	mask = Image.new("L", (pixels, pixels), 0)
	ImageDraw.Draw(mask).rounded_rectangle(
		(0, 0, pixels - 1, pixels - 1),
		radius=radius * scale,
		fill=255,
	)
	image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
	return image

def load_logo_image(size: int, corner_radius: int = 0):
	candidates = [path for path in (LOGO_IMAGE_PATH, LOGO_PATH) if path.is_file()]
	if not candidates:
		return None
	try:
		from PIL import Image
		import customtkinter as ctk
	except ImportError:
		return None
	for path in candidates:
		try:
			with Image.open(path) as source:
				sizes = getattr(source, "sizes", None)
				if sizes:
					source.size = max(sizes, key=lambda item: item[0] * item[1])
				image = _rounded_logo_image(source, size, corner_radius)
		except (OSError, ValueError):
			continue
		return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
	return None

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