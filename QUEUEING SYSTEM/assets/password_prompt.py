"""Themed modal prompt for entering a password.

The prompt replaces the native ``tkinter.simpledialog.askstring`` dialog so
that it matches the look of the rest of the application and so that the
password field can offer the same vector visibility toggle used everywhere
else in the app.
"""

import ctypes
import sys
import tkinter
from typing import Any, Optional

import customtkinter as ctk

from assets import set_window_icon
from assets.password_toggle import CLOSED, OPEN, PasswordVisibilityButton

# DWM window attributes used for the dark/light title bar.
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19


class _PromptToplevel(ctk.CTkToplevel):
	"""A ``CTkToplevel`` that recolours the title bar without hiding the window.

	CustomTkinter's default implementation recolours the Windows title bar by
	withdrawing the window and showing it again a few milliseconds later.
	Windows delivers such a show-cycle as a synthetic mouse click at the
	current cursor position, so a dialog that opens while the cursor happens
	to rest over one of its buttons immediately triggers that button - the
	prompt would cancel itself before the user even typed anything.

	Recolouring the title bar in place keeps the dark title bar of the rest
	of the app while removing the withdraw/show cycle that causes the stray
	click.
	"""

	def _windows_set_titlebar_color(self, color_mode: str) -> None:
		if not sys.platform.startswith("win"):
			return

		if color_mode.lower() == "dark":
			value = 1
		elif color_mode.lower() == "light":
			value = 0
		else:
			return

		try:
			# Make sure the native window handle exists before asking for it.
			self.update_idletasks()
			hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
			attribute = ctypes.c_int(value)
			size = ctypes.sizeof(attribute)
			if ctypes.windll.dwmapi.DwmSetWindowAttribute(
				hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(attribute), size
			) != 0:
				ctypes.windll.dwmapi.DwmSetWindowAttribute(
					hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1, ctypes.byref(attribute), size
				)
		except Exception:
			pass


class PasswordPrompt:
	"""Modal dialog that asks for a password and returns it (or ``None``)."""

	def __init__(
		self,
		master: Any,
		title: str,
		message: str,
		placeholder_text: str = "Password",
		confirm_text: str = "Continue",
		width: int = 400,
	) -> None:
		self.result: Optional[str] = None
		self._show_password = False
		self._focus_job: Optional[str] = None

		self.window = _PromptToplevel(master)
		self.window.title(title)
		self.window.geometry(f"{width}x250")
		self.window.resizable(False, False)
		self.window.transient(master.winfo_toplevel())
		set_window_icon(self.window)
		self.window.grid_columnconfigure(0, weight=1)

		ctk.CTkLabel(
			self.window,
			text=title.upper(),
			font=ctk.CTkFont(family="Bahnschrift", size=15, weight="bold"),
			text_color=("#397A45", "#66A873"),
		).grid(row=0, column=0, pady=(22, 6))
		ctk.CTkLabel(
			self.window,
			text=message,
			font=ctk.CTkFont(family="Bahnschrift", size=11),
			text_color=("#183B22", "#E4EEE5"),
			wraplength=width - 44,
		).grid(row=1, column=0, pady=(0, 8))

		password_frame = ctk.CTkFrame(self.window, fg_color="transparent")
		password_frame.grid(row=2, column=0, padx=22, pady=6, sticky="ew")
		password_frame.grid_columnconfigure(0, weight=1)

		self.entry = ctk.CTkEntry(
			password_frame,
			placeholder_text=placeholder_text,
			show="*",
			font=ctk.CTkFont(family="Bahnschrift", size=12),
		)
		self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

		self.toggle_button = PasswordVisibilityButton(
			password_frame,
			command=self._toggle_visibility,
			width=30,
			height=30,
		)
		self.toggle_button.grid(row=0, column=1)

		actions = ctk.CTkFrame(self.window, fg_color="transparent")
		actions.grid(row=3, column=0, padx=22, pady=(8, 18), sticky="ew")
		actions.grid_columnconfigure((0, 1), weight=1)

		ctk.CTkButton(
			actions,
			text="Cancel",
			command=self._cancel,
			font=ctk.CTkFont(family="Bahnschrift", size=12),
			fg_color="transparent",
			border_width=1,
			border_color=("#BCD5BE", "#405944"),
			text_color=("#183B22", "#E4EEE5"),
		).grid(row=0, column=0, padx=(0, 6), sticky="ew")
		ctk.CTkButton(
			actions,
			text=confirm_text,
			command=self._confirm,
			font=ctk.CTkFont(family="Bahnschrift", size=12, weight="bold"),
			fg_color=("#397A45", "#66A873"),
			hover_color=("#2F6639", "#4E8C5A"),
		).grid(row=0, column=1, padx=(6, 0), sticky="ew")

		self.entry.bind("<Return>", lambda _event: self._confirm())
		self.window.bind("<Return>", lambda _event: self._confirm())
		self.window.protocol("WM_DELETE_WINDOW", self._cancel)

	def _toggle_visibility(self) -> None:
		self._show_password = not self._show_password
		self.entry.configure(show="" if self._show_password else "*")
		self.toggle_button.set_state(OPEN if self._show_password else CLOSED)

	def _confirm(self) -> None:
		self.result = self.entry.get()
		self._close()

	def _cancel(self) -> None:
		self.result = None
		self._close()

	def _close(self) -> None:
		if self._focus_job is not None:
			try:
				self.window.after_cancel(self._focus_job)
			except tkinter.TclError:
				pass
			self._focus_job = None
		self.window.destroy()

	def show(self) -> Optional[str]:
		"""Display the dialog modally and return the entered password."""
		self.window.deiconify()
		self.window.lift()
		# The window is grabbed and focused once it is actually mapped on
		# screen, so that the caret ends up in the password field.
		self._focus_job = self.window.after(10, self._focus_entry)
		self.window.wait_window()
		return self.result

	def _focus_entry(self) -> None:
		self._focus_job = None
		if not self.window.winfo_exists():
			return
		try:
			if not self.window.winfo_ismapped():
				# Not on screen yet: try again in a moment.
				self._focus_job = self.window.after(20, self._focus_entry)
				return
			self.window.grab_set()
			self.entry.focus_force()
		except tkinter.TclError:
			pass


def prompt_for_password(
	master: Any,
	title: str,
	message: str,
	placeholder_text: str = "Password",
	confirm_text: str = "Continue",
	width: int = 400,
) -> Optional[str]:
	"""Ask for a password in a themed dialog; returns ``None`` if cancelled."""
	prompt = PasswordPrompt(
		master,
		title,
		message,
		placeholder_text=placeholder_text,
		confirm_text=confirm_text,
		width=width,
	)
	return prompt.show()
