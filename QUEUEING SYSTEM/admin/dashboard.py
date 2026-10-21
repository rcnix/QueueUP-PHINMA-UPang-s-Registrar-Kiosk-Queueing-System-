import calendar as month_calendar
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import simpledialog, ttk
from datetime import date, timedelta

import customtkinter as ctk
import psycopg2
from tkcalendar import DateEntry

from admin.calendar import AdminCalendarMixin
from admin.concerns import ConcernManagementMixin
from admin.counters import CounterCreationMixin
from admin.styles import (
	ADMIN_BACKGROUND,
	ADMIN_CANVAS,
	BORDER,
	FONT_FAMILY,
	GREEN,
	GREEN_HOVER,
	HOVER_GREEN,
	INK,
	MUTED_GREEN,
	MUTED_TEXT,
	PALE_BORDER,
	PALE_GREEN,
	SOFT_BORDER,
	SOFT_GREEN,
	SOFT_GREEN_HOVER,
	SURFACE,
	SURFACE_ALT,
)
from admin.validation import set_field_error
from assets import (
	format_counter_label,
	layout_responsive_grid,
	set_window_icon,
)
from database.queries import (
	delete_all_application_data,
	get_concerns,
	get_counters,
	get_faqs,
	get_kiosk_login_username,
	get_latest_tickets,
	get_queue_snapshot,
	get_transactions,
	configure_kiosk_login,
	delete_faq,
	save_faq,
	verify_admin_password,
)


class AdminDashboard(CounterCreationMixin, ConcernManagementMixin, AdminCalendarMixin, ctk.CTkFrame):
	TABLE_WEIGHTS = (1.0, 0.65, 0.8, 1.8, 1.25, 1.25, 1.25)
	ADMIN_SECTIONS = (
		"Live Queues",
		"Transactions",
		"Concerns",
		"Calendar",
		"FAQ Editor",
		"Counter Creation",
		"Kiosk User",
	)

	def __init__(self, root, on_logout=None, on_delete_account=None):
		super().__init__(root, corner_radius=0)
		self.on_logout = on_logout
		self.on_delete_account = on_delete_account
		self.status = tk.StringVar(value="Administrative view connected.")
		self._refresh_job = None
		self._waiting_by_counter: dict[int, list[str]] = {}
		self._queue_hover_windows = {}
		self._queue_hover_jobs = {}
		self._tab_refresh_job = None
		self._initialize_calendar()
		self._transaction_filter_window = None
		self.faq_editor_id: int | None = None
		self._settings_window = None
		self._email_update_window = None
		self.counter_number_by_label: dict[str, int] = {}
		self._counter_filter_menus = []
		self._section_drawer_width = round(self._apply_widget_scaling(280))
		self._section_drawer_x = -self._section_drawer_width
		self._section_drawer_open = False
		self._section_drawer_animation_job = None
		self._section_overlay = None
		self._section_drawer_window = None
		self._root_configure_job = None
		self._section_nav_buttons: dict[str, ctk.CTkButton] = {}
		self._root_configure_binding_id = self.winfo_toplevel().bind(
			"<Configure>", self._on_root_configure, add="+"
		)
		self._date_entries = []
		self._ttk_style = ttk.Style(self)
		self.pack(fill="both", expand=True)
		self._build_ui()
		self._apply_native_widget_theme()
		self._refresh_live_queues()

	def _build_ui(self) -> None:
		self.configure(fg_color=ADMIN_BACKGROUND)
		header = ctk.CTkFrame(self, fg_color="transparent")
		header.pack(fill="x", padx=22, pady=(14, 4))
		header.grid_columnconfigure((0, 2), weight=1, uniform="header-side")
		self.section_button = ctk.CTkButton(
			header,
			text="\u2630",
			width=42,
			command=self._toggle_section_drawer,
			font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
		)
		self.section_button.grid(row=0, column=0, sticky="w", padx=(0, 12))
		ctk.CTkLabel(
			header,
			text="QueueUP Admin",
			font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
			text_color=INK,
		).grid(row=0, column=1)
		self.active_section_label = tk.StringVar(value="LIVE QUEUES")
		ctk.CTkLabel(
			header,
			textvariable=self.active_section_label,
			fg_color=PALE_GREEN,
			text_color=GREEN,
			corner_radius=6,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			padx=12,
			pady=7,
		).grid(row=0, column=2, sticky="e")
		self.tabs = ctk.CTkFrame(
			self,
			fg_color=ADMIN_CANVAS,
			corner_radius=16,
		)
		self.tabs.pack(fill="both", expand=True, padx=22, pady=(8, 12))
		self.tabs.grid_rowconfigure(0, weight=1)
		self.tabs.grid_columnconfigure(0, weight=1)
		self._admin_tab_frames = {
			section: ctk.CTkFrame(self.tabs, fg_color="transparent", corner_radius=0)
			for section in self.ADMIN_SECTIONS
		}
		self._build_live_tab(self._admin_tab_frames["Live Queues"])
		self._build_transactions_tab(self._admin_tab_frames["Transactions"])
		self._build_concerns_tab(self._admin_tab_frames["Concerns"])
		self._build_calendar_tab(self._admin_tab_frames["Calendar"])
		self._build_faq_editor_tab(self._admin_tab_frames["FAQ Editor"])
		self._build_counter_creation_tab(self._admin_tab_frames["Counter Creation"])
		self._build_kiosk_user_tab(self._admin_tab_frames["Kiosk User"])
		self._active_admin_section = "Live Queues"
		self._admin_tab_frames[self._active_admin_section].grid(
			row=0, column=0, padx=12, pady=12, sticky="nsew"
		)
		self._build_section_drawer()
		self._update_section_drawer_selection()

	def _build_section_drawer(self) -> None:
		root = self.winfo_toplevel()
		self._section_drawer_window = tk.Toplevel(root)
		self._section_drawer_window.overrideredirect(True)
		self._section_drawer_window.transient(root)
		mode = 1 if ctk.get_appearance_mode().lower() == "dark" else 0
		self._section_drawer_window.configure(background=SURFACE[mode])
		self._section_drawer_window.withdraw()
		self.section_drawer = ctk.CTkFrame(
			self._section_drawer_window,
			width=280,
			corner_radius=0,
			fg_color=SURFACE,
		)
		self.section_drawer.pack(fill="both", expand=True)
		self.section_drawer.pack_propagate(False)
		drawer_header = ctk.CTkFrame(self.section_drawer, fg_color="transparent")
		drawer_header.pack(fill="x", padx=16, pady=(20, 16))
		drawer_header.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			drawer_header,
			text="ADMIN MENU",
			font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
			text_color=GREEN,
			anchor="w",
		).grid(row=0, column=0, sticky="w")
		ctk.CTkButton(
			drawer_header,
			text="\u00d7",
			width=32,
			height=32,
			command=self._toggle_section_drawer,
			fg_color="transparent",
			hover_color=SOFT_GREEN,
			text_color=INK,
			font=ctk.CTkFont(family=FONT_FAMILY, size=22),
		).grid(row=0, column=1, sticky="e")
		section_list = ctk.CTkFrame(self.section_drawer, fg_color="transparent")
		self._section_nav_buttons = {}
		for section in self.ADMIN_SECTIONS:
			button = ctk.CTkButton(
				section_list,
				text=section,
				height=44,
				command=lambda name=section: self._select_section(name),
				font=ctk.CTkFont(family=FONT_FAMILY, size=15),
				fg_color="transparent",
				hover_color=GREEN_HOVER,
				text_color=INK,
				anchor="w",
			)
			button.pack(fill="x", padx=10, pady=2)
			self._section_nav_buttons[section] = button
		section_list.pack(fill="both", expand=True, padx=10)
		settings_footer = ctk.CTkFrame(
			self.section_drawer,
			fg_color="transparent",
		)
		settings_footer.pack(side="bottom", fill="x", padx=10, pady=(0, 14))
		ctk.CTkFrame(settings_footer, height=1, fg_color=SOFT_GREEN).pack(
			fill="x", padx=6, pady=(8, 10)
		)
		ctk.CTkButton(
			settings_footer,
			text="Settings",
			height=40,
			command=self._open_settings_from_drawer,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
			fg_color="transparent",
			hover_color=HOVER_GREEN,
			text_color=INK,
			anchor="w",
		).pack(fill="x", padx=10, pady=2)

	def _update_section_drawer_selection(self) -> None:
		for section, button in self._section_nav_buttons.items():
			selected = section == self._active_admin_section
			button.configure(
				fg_color=GREEN if selected else "transparent",
				hover_color=GREEN_HOVER if selected else HOVER_GREEN,
				text_color="white" if selected else INK,
			)

	def _toggle_section_drawer(self) -> None:
		if self._section_drawer_open:
			self._section_drawer_open = False
		else:
			self._open_section_drawer()
		if self._section_drawer_animation_job is not None:
			self.after_cancel(self._section_drawer_animation_job)
			self._section_drawer_animation_job = None
		self._animate_section_drawer()

	def _open_section_drawer(self) -> None:
		self._section_drawer_open = True
		root = self.winfo_toplevel()
		self.update_idletasks()
		self._section_overlay = tk.Toplevel(root)
		self._section_overlay.overrideredirect(True)
		self._section_overlay.transient(root)
		self._section_overlay.configure(background="black")
		self._section_overlay.attributes("-alpha", 0.4)
		self._section_overlay.bind(
			"<Button-1>", lambda _event: self._toggle_section_drawer()
		)
		self._section_drawer_window.deiconify()
		self._position_section_overlay()
		self._raise_section_windows()

	def _raise_section_windows(self) -> None:
		root = self.winfo_toplevel()
		if self._section_overlay is not None and self._section_overlay.winfo_exists():
			self._section_overlay.lift(root)
		if (
			self._section_drawer_window is not None
			and self._section_drawer_window.winfo_exists()
		):
			self._section_drawer_window.lift()

	def _position_section_overlay(self, _event=None, *, raise_windows: bool = True) -> None:
		if not self._section_drawer_open:
			return
		root = self.winfo_toplevel()
		width = max(root.winfo_width(), 1)
		height = max(root.winfo_height(), 1)
		root_x = root.winfo_rootx()
		root_y = root.winfo_rooty()
		drawer_width = max(1, self._section_drawer_width + self._section_drawer_x)
		if self._section_overlay is not None and self._section_overlay.winfo_exists():
			self._section_overlay.geometry(
				f"{width}x{height}"
				f"{self._geometry_offset(root_x, root.winfo_screenwidth(), width)}"
				f"{self._geometry_offset(root_y, root.winfo_screenheight(), height)}"
			)
		if (
			self._section_drawer_window is not None
			and self._section_drawer_window.winfo_exists()
		):
			self._section_drawer_window.geometry(
				f"{drawer_width}x{height}"
				f"{self._geometry_offset(root_x, root.winfo_screenwidth(), drawer_width)}"
				f"{self._geometry_offset(root_y, root.winfo_screenheight(), height)}"
			)
		if raise_windows:
			self._raise_section_windows()

	@staticmethod
	def _geometry_offset(position: int, screen_size: int, window_size: int) -> str:
		if position >= 0:
			return f"+{position}"
		return f"-{screen_size - position - window_size}"

	def _on_root_configure(self, event) -> None:
		if event.widget is not self.winfo_toplevel() or not self._section_drawer_open:
			return
		if self._root_configure_job is not None:
			self.after_cancel(self._root_configure_job)
		self._root_configure_job = self.after(40, self._reposition_section_windows)

	def _reposition_section_windows(self) -> None:
		self._root_configure_job = None
		self._position_section_overlay(raise_windows=False)

	def _animate_section_drawer(self) -> None:
		target_x = 0 if self._section_drawer_open else -self._section_drawer_width
		if self._section_drawer_x < target_x:
			self._section_drawer_x = min(target_x, self._section_drawer_x + 56)
		elif self._section_drawer_x > target_x:
			self._section_drawer_x = max(target_x, self._section_drawer_x - 56)
		self._position_section_overlay()
		if self._section_drawer_x != target_x:
			self._section_drawer_animation_job = self.after(
				16, self._animate_section_drawer
			)
			return
		self._section_drawer_animation_job = None
		if not self._section_drawer_open:
			self._section_drawer_window.withdraw()
			if self._section_overlay is not None:
				self._section_overlay.destroy()
				self._section_overlay = None

	def _select_section(self, section: str) -> None:
		self._admin_tab_frames[self._active_admin_section].grid_remove()
		self._active_admin_section = section
		self.active_section_label.set(section.upper())
		self._update_section_drawer_selection()
		self._admin_tab_frames[section].grid(
			row=0, column=0, padx=12, pady=12, sticky="nsew"
		)
		self._on_admin_tab_changed()
		if self._section_drawer_open:
			self._toggle_section_drawer()

	def _open_settings_from_drawer(self) -> None:
		if self._section_drawer_open:
			self._toggle_section_drawer()
		self._show_settings()

	def _on_counters_changed(self) -> None:
		self._refresh_counter_filter_menus()
		self._render_live_counter_panels()
		self._refresh_live_queues()
		if hasattr(self, "concern_list"):
			self._refresh_concerns()
		if hasattr(self, "faq_target_menu"):
			self._refresh_faq_editor_targets()

	def _counter_filter_values(self) -> list[str]:
		try:
			counters = get_counters()
		except psycopg2.Error as error:
			self.status.set(f"Could not load counters: {error}")
			counters = []
		self.counter_number_by_label = {
			format_counter_label(number, name): number
			for number, name, _prefix, _username in counters
		}
		return ["ALL COUNTERS", *self.counter_number_by_label]

	def _refresh_counter_filter_menus(self) -> None:
		values = self._counter_filter_values()
		for menu, variable in self._counter_filter_menus:
			try:
				menu.configure(values=values)
				if variable.get() not in values:
					variable.set("ALL COUNTERS")
			except tk.TclError:
				pass

	def _counter_number_from_label(self, label: str) -> int | None:
		if label == "ALL COUNTERS":
			return None
		return self.counter_number_by_label.get(label)

	def _build_kiosk_user_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		card = ctk.CTkFrame(
			tab,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
			corner_radius=8,
		)
		card.grid(row=0, column=0, padx=24, pady=12, sticky="n")
		card.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			card,
			text="CREATE OR UPDATE KIOSK USER",
			font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
			text_color=GREEN,
			anchor="w",
		).grid(row=0, column=0, padx=20, pady=(14, 6), sticky="ew")
		ctk.CTkLabel(
			card,
			text="Set the shared credentials used by the Kiosk User option on the login screen.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			text_color=INK,
			wraplength=700,
			anchor="w",
			justify="left",
		).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
		ctk.CTkLabel(
			card,
			text="Kiosk username",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=2, column=0, padx=20, pady=(4, 2), sticky="ew")
		try:
			username = get_kiosk_login_username()
		except psycopg2.Error as error:
			self.status.set(f"Could not load kiosk account: {error}")
			username = None
		self.kiosk_username_entry = ctk.CTkEntry(
			card,
			height=34,
			placeholder_text="Shared kiosk username",
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
		)
		self.kiosk_username_entry.grid(row=3, column=0, padx=20, pady=(0, 6), sticky="ew")
		self.kiosk_username_error = ctk.CTkLabel(
			card,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.kiosk_username_error.grid(row=4, column=0, padx=20, sticky="ew")
		if username is not None:
			self.kiosk_username_entry.insert(0, username)
		ctk.CTkLabel(
			card,
			text="Kiosk password",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=5, column=0, padx=20, pady=(4, 2), sticky="ew")
		self.kiosk_password_frame = ctk.CTkFrame(card, fg_color="transparent")
		self.kiosk_password_frame.grid(row=6, column=0, padx=20, pady=(0, 2), sticky="ew")
		self.kiosk_password_frame.grid_columnconfigure(0, weight=1)
		self.kiosk_password_entry = ctk.CTkEntry(
			self.kiosk_password_frame,
			height=34,
			placeholder_text="Set or replace kiosk password",
			show="*",
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
		)
		self.kiosk_password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._kiosk_show_password = False
		self.show_kiosk_password_btn = ctk.CTkButton(
			self.kiosk_password_frame,
			text="✭",
			width=30,
			command=self._toggle_kiosk_password_visibility,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
		)
		self.show_kiosk_password_btn.grid(row=0, column=1)
		self.kiosk_password_error = ctk.CTkLabel(
			card,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.kiosk_password_error.grid(row=7, column=0, padx=20, sticky="ew")
		ctk.CTkLabel(
			card,
			text="Confirm kiosk password",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=8, column=0, padx=20, pady=(4, 2), sticky="ew")
		self.kiosk_confirm_frame = ctk.CTkFrame(card, fg_color="transparent")
		self.kiosk_confirm_frame.grid(row=9, column=0, padx=20, pady=(0, 2), sticky="ew")
		self.kiosk_confirm_frame.grid_columnconfigure(0, weight=1)
		self.kiosk_confirm_entry = ctk.CTkEntry(
			self.kiosk_confirm_frame,
			height=34,
			placeholder_text="Re-enter kiosk password",
			show="*",
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
		)
		self.kiosk_confirm_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._kiosk_show_confirm = False
		self.show_kiosk_confirm_btn = ctk.CTkButton(
			self.kiosk_confirm_frame,
			text="✭",
			width=30,
			command=self._toggle_kiosk_confirm_visibility,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
		)
		self.show_kiosk_confirm_btn.grid(row=0, column=1)
		self.kiosk_confirm_error = ctk.CTkLabel(
			card,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.kiosk_confirm_error.grid(row=10, column=0, padx=20, sticky="ew")
		self.kiosk_status = ctk.CTkLabel(
			card,
			text=(
				"Kiosk user is configured. Enter a new password to replace it."
				if username is not None
				else "No kiosk user exists yet."
			),
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="w",
		)
		self.kiosk_status.grid(row=11, column=0, padx=20, pady=(0, 6), sticky="ew")
		ctk.CTkButton(
			card,
			text="Save Kiosk User",
			command=self._save_kiosk_credentials,
			height=36,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=12, column=0, padx=20, pady=(2, 14), sticky="ew")

	def _toggle_kiosk_password_visibility(self) -> None:
		self._kiosk_show_password = not self._kiosk_show_password
		self.kiosk_password_entry.configure(show="" if self._kiosk_show_password else "*")
		self.show_kiosk_password_btn.configure(
			text="⭑" if self._kiosk_show_password else "✭"
		)

	def _toggle_kiosk_confirm_visibility(self) -> None:
		self._kiosk_show_confirm = not self._kiosk_show_confirm
		self.kiosk_confirm_entry.configure(show="" if self._kiosk_show_confirm else "*")
		self.show_kiosk_confirm_btn.configure(
			text="⭑" if self._kiosk_show_confirm else "✭"
		)


	def _show_settings(self) -> None:
		if self._settings_window is not None and self._settings_window.winfo_exists():
			self._settings_window.deiconify()
			self._settings_window.lift()
			return
		window = ctk.CTkToplevel(self)
		self._settings_window = window
		window.title("Admin Settings")
		window.geometry("310x300")
		window.resizable(False, False)
		window.transient(self.winfo_toplevel())
		set_window_icon(window)
		window.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			window,
			text="ADMIN SETTINGS",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, padx=20, pady=(18, 10), sticky="w")
		dark_mode = tk.BooleanVar(value=ctk.get_appearance_mode().lower() == "dark")
		ctk.CTkSwitch(
			window,
			text="Dark mode",
			variable=dark_mode,
			command=lambda: self._set_admin_appearance_mode(dark_mode.get()),
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		).grid(row=1, column=0, padx=20, pady=10, sticky="w")
		ctk.CTkButton(
			window,
			text="Set Recovery Email",
			command=self._set_admin_recovery_email,
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
		).grid(row=2, column=0, padx=20, pady=6, sticky="ew")
		ctk.CTkButton(
			window,
			text="Log Out",
			command=lambda: self._logout(window),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=3, column=0, padx=20, pady=6, sticky="ew")
		ctk.CTkButton(
			window,
			text="Delete Admin Account",
			command=lambda: self._delete_admin_account(window),
			fg_color="#A64C42",
			hover_color="#873C34",
		).grid(row=4, column=0, padx=20, pady=(6, 18), sticky="ew")

	def _set_admin_recovery_email(self) -> None:
		if (
			self._email_update_window is not None
			and self._email_update_window.winfo_exists()
		):
			self._email_update_window.lift()
			return
		from application import AdminEmailUpdateWindow

		self._email_update_window = AdminEmailUpdateWindow(
			self,
			lambda: self.status.set("Admin recovery email updated."),
		)

	def _set_admin_appearance_mode(self, dark_mode: bool) -> None:
		ctk.set_appearance_mode("Dark" if dark_mode else "Light")
		self._apply_native_widget_theme()

	def _apply_native_widget_theme(self) -> None:
		mode = 1 if ctk.get_appearance_mode().lower() == "dark" else 0
		surface = SURFACE[mode]
		surface_alt = SURFACE_ALT[mode]
		ink = INK[mode]
		border = BORDER[mode]
		muted = MUTED_TEXT[mode]
		if "clam" in self._ttk_style.theme_names():
			self._ttk_style.theme_use("clam")
		self._ttk_style.configure(
			"QueueUP.TEntry",
			fieldbackground=surface,
			foreground=ink,
			insertcolor=ink,
			bordercolor=border,
			lightcolor=border,
			darkcolor=border,
		)
		self._ttk_style.map(
			"QueueUP.TEntry",
			fieldbackground=[("disabled", surface_alt)],
			foreground=[("disabled", muted)],
		)
		for date_entry in self._date_entries:
			if not date_entry.winfo_exists():
				continue
			date_entry.configure(
				background=surface,
				foreground=ink,
				bordercolor=border,
				headersbackground=surface_alt,
				headersforeground=ink,
				selectbackground=GREEN[mode],
				selectforeground="#FFFFFF",
				normalbackground=surface,
				normalforeground=ink,
				weekendbackground=surface,
				weekendforeground=ink,
				othermonthbackground=surface_alt,
				othermonthforeground=muted,
			)

	def _save_kiosk_credentials(self) -> None:
		if not self._validate_kiosk_form():
			return
		username = self.kiosk_username_entry.get().strip()
		password = self.kiosk_password_entry.get()
		try:
			configure_kiosk_login(username, password)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror(
				"Could not save kiosk credentials",
				str(error),
				parent=self,
			)
			return
		self.kiosk_password_entry.delete(0, "end")
		self.kiosk_confirm_entry.delete(0, "end")
		self.kiosk_status.configure(
			text="Kiosk credentials saved. The password is stored as a one-way hash.",
			text_color=GREEN,
		)
		self.status.set("Kiosk login credentials updated.")

	def _validate_kiosk_form(self, show_required: bool = True) -> bool:
		username_message = (
			"Kiosk username is required."
			if show_required and not self.kiosk_username_entry.get().strip()
			else ""
		)
		password = self.kiosk_password_entry.get()
		password_message = (
			"Kiosk password is required."
			if show_required and not password
			else ""
		)
		confirmation = self.kiosk_confirm_entry.get()
		confirm_message = (
			"Passwords do not match."
			if confirmation and confirmation != password
			else "Confirm the kiosk password."
			if show_required and not confirmation
			else ""
		)
		set_field_error(
			self.kiosk_username_entry,
			self.kiosk_username_error,
			username_message,
		)
		set_field_error(
			self.kiosk_password_entry,
			self.kiosk_password_error,
			password_message,
		)
		set_field_error(
			self.kiosk_confirm_entry,
			self.kiosk_confirm_error,
			confirm_message,
		)
		return not (username_message or password_message or confirm_message)

	def _logout(self, settings_window) -> None:
		settings_window.destroy()
		if self.on_logout is not None:
			self.on_logout()

	def _delete_admin_account(self, settings_window) -> None:
		password = simpledialog.askstring(
			"Confirm current password",
			"Enter your current admin password to continue:",
			show="*",
			parent=settings_window,
		)
		if password is None:
			return
		try:
			verified = verify_admin_password(password)
		except psycopg2.Error as error:
			messagebox.showerror("Deletion cancelled", str(error), parent=settings_window)
			return
		if not verified:
			messagebox.showerror(
				"Incorrect password",
				"The current admin password is incorrect. Deletion cancelled.",
				parent=settings_window,
			)
			return
		if not messagebox.askyesno(
			"Delete admin account and all data?",
			"This permanently deletes the admin account, counter accounts, counters, "
			"concerns, FAQs, tickets, and transaction history. This cannot be undone.\n\n"
			"Continue?",
			icon="warning",
			parent=settings_window,
		):
			return
		try:
			delete_all_application_data()
		except psycopg2.Error as error:
			messagebox.showerror("Account deletion failed", str(error), parent=settings_window)
			return
		settings_window.destroy()
		messagebox.showinfo(
			"Admin account deleted",
			"All QueueUP data was deleted. Create a new admin account to continue.",
			parent=self,
		)
		if self.on_delete_account is not None:
			self.on_delete_account()

	def _build_live_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(1, weight=1)
		header = ctk.CTkFrame(
			tab,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
			corner_radius=8,
		)
		header.grid(row=0, column=0, padx=8, pady=(8, 4), sticky="ew")
		header.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			header,
			text="LIVE QUEUES",
			font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=0, column=0, padx=16, pady=(10, 0), sticky="w")
		ctk.CTkLabel(
			header,
			text="Current counter activity and waiting tickets",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=MUTED_TEXT,
			anchor="w",
		).grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")
		self.live_queue_summary = tk.StringVar(value="LIVE  |  0 COUNTERS  |  0 WAITING")
		summary_badge = ctk.CTkLabel(
			header,
			textvariable=self.live_queue_summary,
			fg_color=PALE_GREEN,
			text_color=GREEN,
			corner_radius=6,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			padx=12,
			pady=8,
		)
		summary_badge.grid(row=0, column=1, rowspan=2, padx=14, pady=10, sticky="e")
		self.live_grid = ctk.CTkFrame(tab, fg_color="transparent", corner_radius=0)
		self.live_grid.grid(row=1, column=0, sticky="nsew")
		self.live_grid.grid_columnconfigure(0, weight=1)
		self.live_grid.grid_rowconfigure(0, weight=1)
		self.live_queue_status = tk.StringVar(value="Live queue status")
		ctk.CTkLabel(
			tab,
			textvariable=self.live_queue_status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=MUTED_TEXT,
			anchor="center",
		).grid(row=2, column=0, padx=8, pady=(4, 8), sticky="ew")
		self._live_grid_columns = 0
		self._live_panels_rendering = False
		self.live_panel_container = self.live_grid
		self._render_live_counter_panels()

	def _render_live_counter_panels(self) -> None:
		self._live_panels_rendering = True
		self._live_grid_columns = 0
		for child in self.live_grid.winfo_children():
			child.destroy()
		self.latest_labels = {}
		self.serving_labels = {}
		self.count_labels = {}
		self.queue_views = {}
		self.empty_queue_labels = {}
		self.queue_panels = {}
		try:
			counters = get_counters()
		except psycopg2.Error as error:
			self.status.set(f"Could not load counters: {error}")
			counters = []
		counter_label = "COUNTER" if len(counters) == 1 else "COUNTERS"
		self.live_queue_summary.set(
			f"LIVE  |  {len(counters)} {counter_label}  |  0 WAITING"
		)
		if not counters:
			empty_state = ctk.CTkFrame(
				self.live_grid,
				fg_color=SURFACE,
				border_width=1,
				border_color=BORDER,
				corner_radius=8,
			)
			empty_state.grid(row=0, column=0, padx=16, pady=16, sticky="ew")
			empty_state.grid_columnconfigure(0, weight=1)
			ctk.CTkLabel(
				empty_state,
				text="No counters are configured",
				font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
				text_color=INK,
			).grid(row=0, column=0, padx=16, pady=(14, 2))
			ctk.CTkLabel(
				empty_state,
				text="Create a counter account to start monitoring live queues.",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color=MUTED_TEXT,
			).grid(row=1, column=0, padx=16, pady=(0, 14))
			self._live_panels_rendering = False
			return
		self.live_panel_container = ctk.CTkScrollableFrame(
			self.live_grid,
			fg_color="transparent",
			corner_radius=0,
		)
		self.live_panel_container.grid(row=0, column=0, sticky="nsew")
		self.live_panel_container.bind(
			"<Configure>", self._layout_live_counter_panels, add="+"
		)
		self.live_panel_container._responsive_grid_columns = 0
		for index, (counter_number, counter_name, _prefix, _username) in enumerate(
			sorted(counters, key=lambda counter: counter[0])
		):
			row, column = divmod(index, 3)
			panel = ctk.CTkFrame(
				self.live_panel_container,
				width=280,
				height=280,
				fg_color=SURFACE,
				border_width=1,
				border_color=BORDER,
				corner_radius=8,
			)
			panel.grid(
				row=row,
				column=column,
				padx=8,
				pady=8,
				sticky="nsew",
			)
			panel.grid_columnconfigure(0, weight=1)
			panel.grid_rowconfigure(6, weight=1)
			counter_title = ctk.CTkLabel(
				panel,
				text=counter_name,
				font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
				text_color=INK,
				anchor="w",
			)
			counter_title.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")
			ctk.CTkLabel(
				panel,
				text="LATEST TICKET",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=MUTED_GREEN,
				height=18,
				anchor="w",
			).grid(row=1, column=0, padx=14, pady=(1, 0), sticky="ew")
			latest = ctk.CTkLabel(
				panel,
				text="--",
				font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
				text_color=INK,
				anchor="w",
			)
			latest.grid(row=2, column=0, padx=14, pady=(0, 6), sticky="ew")
			self.latest_labels[counter_number] = latest
			serving_panel = ctk.CTkFrame(
				panel,
				fg_color=SURFACE_ALT,
				border_width=1,
				border_color=PALE_BORDER,
				corner_radius=6,
			)
			serving_panel.grid(row=3, column=0, padx=10, pady=2, sticky="ew")
			serving_panel.grid_columnconfigure(0, weight=1)
			ctk.CTkLabel(
				serving_panel,
				text="NOW SERVING",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=MUTED_GREEN,
				height=18,
				anchor="w",
			).grid(row=0, column=0, padx=10, pady=(7, 0), sticky="ew")
			serving = ctk.CTkLabel(
				serving_panel,
				text="--",
				font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
				text_color=GREEN,
				anchor="w",
			)
			serving.grid(row=1, column=0, padx=10, pady=(0, 7), sticky="ew")
			self.serving_labels[counter_number] = serving
			count = ctk.CTkLabel(
				panel,
				text="0 WAITING",
				fg_color=SOFT_GREEN,
				corner_radius=5,
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=GREEN,
				padx=9,
				pady=4,
			)
			count.grid(row=4, column=0, padx=10, pady=(5, 3), sticky="w")
			self.count_labels[counter_number] = count
			ctk.CTkLabel(
				panel,
				text="WAITING QUEUE",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=MUTED_GREEN,
				height=18,
				anchor="w",
			).grid(row=5, column=0, padx=14, pady=(3, 0), sticky="ew")
			queue_view = ctk.CTkTextbox(
				panel,
				height=54,
				activate_scrollbars=False,
				fg_color=SURFACE_ALT,
				border_color=PALE_BORDER,
				border_width=1,
				text_color=INK,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			)
			queue_view.grid(row=6, column=0, padx=10, pady=(3, 10), sticky="nsew")
			queue_view.configure(state="disabled")
			for hover_target in (queue_view, queue_view._textbox):
				hover_target.bind(
					"<Enter>", lambda event, number=counter_number: self._show_queue_hover(event, number)
				)
				hover_target.bind(
					"<Leave>", lambda _event, number=counter_number: self._schedule_queue_hover_close(number)
				)
			self.queue_views[counter_number] = queue_view
			empty_label = ctk.CTkLabel(
				panel,
				text="Queue is clear",
				height=54,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11),
				text_color=MUTED_GREEN,
				fg_color=SURFACE_ALT,
				anchor="center",
			)
			empty_label.grid(row=6, column=0, padx=10, pady=(3, 10), sticky="nsew")
			empty_label.grid_remove()
			self.empty_queue_labels[counter_number] = empty_label
			self.queue_panels[counter_number] = panel
		self._live_panels_rendering = False
		self._layout_live_counter_panels()

	def _layout_live_counter_panels(self, _event=None) -> None:
		if self._live_panels_rendering or not self.queue_panels:
			return
		width = self.live_panel_container._parent_frame.winfo_width()
		if width <= 1:
			return
		self._live_grid_columns = layout_responsive_grid(
			self.live_panel_container,
			list(self.queue_panels.values()),
			width,
			minimum_item_width=320,
			padding=8,
			expand_rows=True,
		)

	def _refresh_live_queues(self) -> None:
		try:
			snapshot = get_queue_snapshot()
			latest_tickets = get_latest_tickets()
			total_waiting = 0
			for counter_number, view in self.queue_views.items():
				serving, waiting = snapshot.get(counter_number, (None, []))
				total_waiting += len(waiting)
				self.latest_labels[counter_number].configure(
					text=latest_tickets.get(counter_number) or "--"
				)
				self.serving_labels[counter_number].configure(text=serving or "--")
				self.count_labels[counter_number].configure(
					text=f"{len(waiting)} WAITING"
				)
				self._waiting_by_counter[counter_number] = list(waiting)
				if waiting:
					self.empty_queue_labels[counter_number].grid_remove()
					view.grid()
					self._set_text(
						view,
						"\n".join(
							f"{position}.  {ticket}"
							for position, ticket in enumerate(waiting, 1)
						),
					)
				else:
					view.grid_remove()
					self.empty_queue_labels[counter_number].grid()
			self.live_queue_summary.set(
				f"LIVE  |  {len(self.queue_views)} "
				f"{'COUNTER' if len(self.queue_views) == 1 else 'COUNTERS'}  |  "
				f"{total_waiting} WAITING"
			)
			self.live_queue_status.set("Live queue status updated.")
		except psycopg2.Error as error:
			self.live_queue_status.set(f"Could not refresh live queues: {error}")
		if self.winfo_exists():
			if self._refresh_job is not None:
				try:
					self.after_cancel(self._refresh_job)
				except tk.TclError:
					pass
			self._refresh_job = self.after(2000, self._refresh_live_queues)

	def _show_queue_hover(self, event, counter_number: int) -> None:
		waiting = self._waiting_by_counter.get(counter_number, [])
		if not waiting or not self._queue_overflows(self.queue_views[counter_number]):
			return
		if counter_number in self._queue_hover_windows:
			return
		popup = ctk.CTkToplevel(self)
		set_window_icon(popup)
		popup.wm_overrideredirect(True)
		popup.geometry(f"+{event.x_root + 14}+{event.y_root + 14}")
		popup.attributes("-topmost", True)
		popup.configure(fg_color=SURFACE)
		self._queue_hover_windows[counter_number] = popup
		popup.bind("<Enter>", lambda _event, number=counter_number: self._cancel_queue_hover_close(number))
		popup.bind("<Leave>", lambda _event, number=counter_number: self._schedule_queue_hover_close(number))
		ctk.CTkLabel(
			popup,
			text=f"COUNTER {counter_number}  /  {len(waiting)} WAITING",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=GREEN,
		).pack(padx=14, pady=(10, 6), anchor="w")
		queue = ctk.CTkScrollableFrame(
			popup,
			width=245,
			height=190,
			fg_color=PALE_GREEN,
		)
		queue.pack(padx=10, pady=(0, 10), fill="both", expand=True)
		for position, ticket in enumerate(waiting, 1):
			ctk.CTkLabel(
				queue,
				text=f"{position:02d}    {ticket}",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color=INK,
				anchor="w",
			).pack(fill="x", padx=6, pady=2)

	@staticmethod
	def _queue_overflows(view) -> bool:
		textbox = view._textbox
		last_line = int(textbox.index("end-1c").split(".")[0])
		line_info = textbox.dlineinfo(f"{last_line}.0")
		return line_info is None or line_info[1] + line_info[3] > textbox.winfo_height()

	def _schedule_queue_hover_close(self, index: int) -> None:
		self._cancel_queue_hover_close(index)
		self._queue_hover_jobs[index] = self.after(
			250, lambda: self._close_queue_hover(index)
		)

	def _cancel_queue_hover_close(self, index: int) -> None:
		job = self._queue_hover_jobs.pop(index, None)
		if job is not None:
			try:
				self.after_cancel(job)
			except tk.TclError:
				pass

	def _close_queue_hover(self, index: int) -> None:
		self._queue_hover_jobs.pop(index, None)
		popup = self._queue_hover_windows.pop(index, None)
		if popup is not None and popup.winfo_exists():
			popup.destroy()

	def _build_transactions_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(1, weight=1)
		controls = ctk.CTkFrame(tab, fg_color="transparent")
		controls.grid(row=0, column=0, padx=10, pady=(10, 6), sticky="ew")
		self._transaction_controls_frame = controls
		self._transaction_controls_wide = None
		controls.bind("<Configure>", self._layout_transaction_controls, add="+")

		def make_control_group(parent, title: str) -> ctk.CTkFrame:
			group = ctk.CTkFrame(
				parent,
				fg_color=SURFACE,
				border_width=1,
				border_color=SOFT_BORDER,
				corner_radius=8,
			)
			ctk.CTkLabel(
				group,
				text=title,
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=MUTED_GREEN,
				anchor="w",
			).pack(fill="x", padx=10, pady=(6, 1))
			return group

		counter_group = make_control_group(controls, "COUNTER")
		self._transaction_counter_group = counter_group
		counter_group.grid(row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="w")
		self.transaction_counter = tk.StringVar(value="ALL COUNTERS")
		self.transaction_counter_menu = ctk.CTkOptionMenu(
			counter_group,
			variable=self.transaction_counter,
			values=self._counter_filter_values(),
			command=lambda _value: self._refresh_transactions(),
			width=130,
			height=34,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.transaction_counter_menu.pack(fill="x", padx=8, pady=(0, 8))
		self._counter_filter_menus.append(
			(self.transaction_counter_menu, self.transaction_counter)
		)

		history_group = make_control_group(controls, "HISTORY RANGE")
		self._transaction_history_group = history_group
		history_group.grid(row=0, column=1, padx=(0, 6), pady=(0, 6), sticky="ew")
		history_controls = ctk.CTkFrame(history_group, fg_color="transparent")
		history_controls.pack(fill="x", padx=6, pady=(0, 6))
		self.all_transactions = tk.BooleanVar(value=False)
		ctk.CTkRadioButton(
			history_controls,
			text="All history",
			variable=self.all_transactions,
			value=True,
			command=self._on_history_mode_changed,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).pack(side="left", padx=(4, 8))
		ctk.CTkRadioButton(
			history_controls,
			text="History date",
			variable=self.all_transactions,
			value=False,
			command=self._on_history_mode_changed,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).pack(side="left", padx=(8, 4))
		self.transaction_history_date = DateEntry(
			history_controls,
			date_pattern="yyyy-mm-dd",
			font=(FONT_FAMILY, 13),
			width=16,
			borderwidth=2,
			style="QueueUP.TEntry",
		)
		self._date_entries.append(self.transaction_history_date)
		self.transaction_history_date.pack(side="left", padx=(6, 2))
		self.transaction_history_date.bind(
			"<<DateEntrySelected>>", self._on_transaction_history_date_selected
		)
		self.transaction_history_date.bind(
			"<FocusOut>", self._on_transaction_history_date_selected, add="+"
		)

		actions_group = make_control_group(controls, "ACTIONS")
		self._transaction_actions_group = actions_group
		actions_group.grid(row=1, column=0, padx=(0, 6), pady=(0, 6), sticky="ew")
		action_buttons = ctk.CTkFrame(actions_group, fg_color="transparent")
		action_buttons.pack(fill="x", padx=6, pady=(0, 6))
		self.transaction_refresh_button = ctk.CTkButton(
			action_buttons,
			text="Refresh Transactions",
			command=self._refresh_transactions,
			width=148,
			height=34,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		)
		self.transaction_refresh_button.pack(side="left", padx=(2, 4))
		ctk.CTkButton(
			action_buttons,
			text="Filter",
			command=self._open_transaction_filter,
			width=86,
			height=34,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
		).pack(side="left", padx=4)

		search_group = make_control_group(controls, "SEARCH")
		self._transaction_search_group = search_group
		search_group.grid(row=1, column=1, padx=(0, 6), pady=(0, 6), sticky="ew")
		search_controls = ctk.CTkFrame(search_group, fg_color="transparent")
		search_controls.pack(fill="x", padx=6, pady=(0, 6))
		self.transaction_search = tk.StringVar(value="")
		ctk.CTkEntry(
			search_controls,
			textvariable=self.transaction_search,
			placeholder_text="Recipient name",
			width=120,
			height=34,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		).pack(side="left", fill="x", expand=True, padx=(2, 4))
		ctk.CTkButton(
			search_controls,
			text="Search",
			width=74,
			command=self._refresh_transactions,
			height=34,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).pack(side="left", padx=4)
		self.transaction_range_label = ctk.CTkLabel(
			controls,
			text="All issued tickets" if self.all_transactions.get() else "",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="e",
		)
		self.transaction_range_label.grid(
			row=1, column=0, columnspan=2, padx=(2, 4), pady=(0, 4), sticky="e"
		)
		self.after_idle(self._layout_transaction_controls)
		self.transaction_filter_date_active = False
		self.transaction_filter_date_value = date.today()
		self.transaction_ticket = tk.StringVar(value="")
		self.transaction_status = tk.StringVar(value="ALL STATUSES")
		column_names = (
			"TICKET",
			"COUNTER",
			"STATUS",
			"RECIPIENT / CONCERN",
			"ISSUED",
			"CALLED",
			"COMPLETED",
		)
		self.transaction_table = ctk.CTkScrollableFrame(
			tab,
			fg_color="transparent",
			corner_radius=0,
		)
		self.transaction_table.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
		for column, (name, weight) in enumerate(zip(column_names, self.TABLE_WEIGHTS)):
			self.transaction_table.grid_columnconfigure(
				column, weight=int(weight * 100), uniform="transaction"
			)
			ctk.CTkLabel(
				self.transaction_table,
				text=name,
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=GREEN,
				fg_color=SOFT_GREEN,
				anchor="center",
				justify="center",
			).grid(row=0, column=column, padx=1, pady=(0, 2), sticky="ew")

	def _layout_transaction_controls(self, event=None) -> None:
		controls = self._transaction_controls_frame
		width = event.width if event is not None else controls.winfo_width()
		if width < 1:
			return
		wide = width >= 1220
		if wide == self._transaction_controls_wide:
			return
		self._transaction_controls_wide = wide
		groups = (
			self._transaction_counter_group,
			self._transaction_history_group,
			self._transaction_actions_group,
			self._transaction_search_group,
		)
		for group in groups:
			group.grid_remove()
		self.transaction_range_label.grid_remove()
		for column in range(4):
			controls.grid_columnconfigure(column, weight=0)
		if wide:
			placements = (
				(self._transaction_counter_group, 0, 0, "w"),
				(self._transaction_history_group, 0, 1, "w"),
				(self._transaction_actions_group, 0, 2, "w"),
				(self._transaction_search_group, 0, 3, "ew"),
			)
			for group, row, column, sticky in placements:
				group.grid(
					row=row,
					column=column,
					padx=(0, 6),
					pady=(0, 2),
					sticky=sticky,
				)
			controls.grid_columnconfigure(3, weight=1)
			self.transaction_range_label.grid(
				row=1, column=0, columnspan=4, padx=(2, 4), pady=(0, 4), sticky="e"
			)
			return
		controls.grid_columnconfigure(1, weight=1)
		placements = (
			(self._transaction_counter_group, 0, 0, "w"),
			(self._transaction_history_group, 0, 1, "ew"),
			(self._transaction_actions_group, 1, 0, "ew"),
			(self._transaction_search_group, 1, 1, "ew"),
		)
		for group, row, column, sticky in placements:
			group.grid(
				row=row,
				column=column,
				padx=(0, 6),
				pady=(0, 4),
				sticky=sticky,
			)
		self.transaction_range_label.grid(
			row=2, column=0, columnspan=2, padx=(2, 4), pady=(0, 4), sticky="e"
		)

	def _on_history_mode_changed(self) -> None:
		self.transaction_history_date.configure(
			state="disabled" if self.all_transactions.get() else "normal"
		)
		self._refresh_transactions()

	def _on_admin_tab_changed(self) -> None:
		if self._tab_refresh_job is not None:
			self.after_cancel(self._tab_refresh_job)
		self._tab_refresh_job = self.after_idle(self._refresh_active_tab)

	def _refresh_active_tab(self) -> None:
		self._tab_refresh_job = None
		selected_tab = self._active_admin_section
		if selected_tab == "Transactions":
			self._refresh_transactions()
		elif selected_tab == "Concerns":
			self._refresh_concerns()
		elif selected_tab == "Calendar":
			self._load_calendar()
		elif selected_tab == "FAQ Editor":
			self._refresh_faq_editor_targets()

	def _open_transaction_filter(self) -> None:
		if self._transaction_filter_window is not None:
			if self._transaction_filter_window.winfo_exists():
				self._transaction_filter_window.deiconify()
				self._transaction_filter_window.lift()
				self._transaction_filter_window.focus_force()
				return
			self._transaction_filter_window = None
		window = ctk.CTkToplevel(self)
		self._transaction_filter_window = window
		window.title("Filter transactions")
		window.geometry("460x400")
		window.minsize(420, 380)
		window.transient(self.winfo_toplevel())
		set_window_icon(window)
		window.grid_columnconfigure(1, weight=1)
		ctk.CTkLabel(
			window,
			text="TRANSACTION FILTERS",
			font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 16), sticky="w")
		ctk.CTkLabel(
			window,
			text="Start date",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=1, column=0, padx=(20, 10), pady=7, sticky="w")
		self.transaction_filter_date_draft_active = self.transaction_filter_date_active
		self.transaction_filter_date_picker = DateEntry(
			window,
			date_pattern="yyyy-mm-dd",
			font=(FONT_FAMILY, 15),
			width=16,
			borderwidth=2,
			style="QueueUP.TEntry",
		)
		self._date_entries.append(self.transaction_filter_date_picker)
		self._apply_native_widget_theme()
		self.transaction_filter_date_picker.set_date(self.transaction_filter_date_value)
		self.transaction_filter_date_picker.bind(
			"<<DateEntrySelected>>", self._on_transaction_filter_date_selected
		)
		self.transaction_filter_date_picker.bind(
			"<FocusOut>", self._on_transaction_filter_date_selected, add="+"
		)
		self.transaction_filter_date_picker.grid(
			row=1, column=1, padx=(0, 20), pady=7, sticky="w"
		)

		fields = (
			("Ticket", "Ticket number contains...", self.transaction_ticket),
			("Recipient", "Recipient name contains...", self.transaction_search),
		)
		for row, (label, placeholder, variable) in enumerate(fields, 2):
			ctk.CTkLabel(
				window,
				text=label,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
				text_color=INK,
				anchor="w",
			).grid(row=row, column=0, padx=(20, 10), pady=7, sticky="w")
			ctk.CTkEntry(
				window,
				textvariable=variable,
				placeholder_text=placeholder,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			).grid(row=row, column=1, padx=(0, 20), pady=7, sticky="ew")

		options = (
			("Counter", self.transaction_counter, self._counter_filter_values()),
			("Status", self.transaction_status, [
				"ALL STATUSES", "WAITING", "SERVING", "COMPLETED", "CANCELLED"
			]),
		)
		for row, (label, variable, values) in enumerate(options, len(fields) + 2):
			ctk.CTkLabel(
				window,
				text=label,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
				text_color=INK,
				anchor="w",
			).grid(row=row, column=0, padx=(20, 10), pady=7, sticky="w")
			menu = ctk.CTkOptionMenu(
				window,
				variable=variable,
				values=values,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				fg_color=GREEN,
				button_color=GREEN_HOVER,
				button_hover_color=INK,
			)
			menu.grid(row=row, column=1, padx=(0, 20), pady=7, sticky="ew")
			if label == "Counter":
				self.transaction_filter_counter_menu = menu
				self._counter_filter_menus.append((menu, variable))
		buttons = ctk.CTkFrame(window, fg_color="transparent")
		buttons.grid(
			row=len(fields) + len(options) + 3,
			column=0,
			columnspan=2,
			padx=20,
			pady=(8, 18),
			sticky="ew",
		)
		ctk.CTkButton(
			buttons,
			text="Reset",
			command=self._reset_transaction_filters,
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		).pack(side="left")
		ctk.CTkButton(
			buttons,
			text="Apply filters",
			command=self._apply_transaction_filters,
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
		).pack(side="right")
		window.protocol("WM_DELETE_WINDOW", self._close_transaction_filter)

	def _apply_transaction_filters(self) -> None:
		self.transaction_filter_date_value = self.transaction_filter_date_picker.get_date()
		self.transaction_filter_date_active = self.transaction_filter_date_draft_active
		self._refresh_transactions()
		self._close_transaction_filter()

	def _close_transaction_filter(self) -> None:
		if self._transaction_filter_window is not None:
			if self._transaction_filter_window.winfo_exists():
				self._transaction_filter_window.destroy()
			self._transaction_filter_window = None

	def _reset_transaction_filters(self) -> None:
		if not messagebox.askyesno(
			"Reset transaction filters",
			"Reset the filters in this dialog? The All history setting will be preserved.",
			parent=self._transaction_filter_window or self,
		):
			return
		self.transaction_filter_date_active = False
		self.transaction_filter_date_draft_active = False
		self.transaction_filter_date_value = date.today()
		if (
			self._transaction_filter_window is not None
			and self._transaction_filter_window.winfo_exists()
		):
			self.transaction_filter_date_picker.set_date(date.today())
		self.transaction_ticket.set("")
		self.transaction_search.set("")
		self.transaction_status.set("ALL STATUSES")
		self.transaction_counter.set("ALL COUNTERS")
		self._refresh_transactions()

	def _on_transaction_filter_date_selected(self, _event=None) -> None:
		self.transaction_filter_date_draft_active = True

	def _on_transaction_history_date_selected(self, _event=None) -> None:
		self._refresh_transactions()

	def _refresh_transactions(self) -> None:
		try:
			selected_counter = self.transaction_counter.get()
			start_date = (
				self.transaction_filter_date_value
				if self.transaction_filter_date_active
				else None
			)
			end_date = None
			if not self.all_transactions.get() and not self.transaction_filter_date_active:
				start_date = self.transaction_history_date.get_date()
				end_date = start_date
			end_date_exclusive = end_date + timedelta(days=1) if end_date else None
			status = self.transaction_status.get().lower()
			status = None if status == "all statuses" else status
			other_filters_active = any((
				self.transaction_filter_date_active,
				self.transaction_ticket.get().strip(),
				self.transaction_search.get().strip(),
				status,
				selected_counter != "ALL COUNTERS",
			))
			self.transaction_range_label.configure(
				text=(
					"All issued tickets"
					if self.all_transactions.get() and not other_filters_active
					else "All matching transactions"
					if other_filters_active
					else f"Tickets on {self.transaction_history_date.get_date():%Y-%m-%d}"
				)
			)
			rows = get_transactions(
				limit=None,
				start_date=start_date,
				end_date=end_date_exclusive,
				counter_number=self._counter_number_from_label(selected_counter),
				search_text=self.transaction_search.get(),
				ticket_number=self.transaction_ticket.get(),
				status=status,
			)
			for child in self.transaction_table.winfo_children():
				child.destroy()
			column_names = (
				"TICKET", "COUNTER", "STATUS", "RECIPIENT / CONCERN",
				"ISSUED", "CALLED", "COMPLETED",
			)
			for column, (name, weight) in enumerate(zip(column_names, self.TABLE_WEIGHTS)):
				self.transaction_table.grid_columnconfigure(
					column, weight=int(weight * 100), uniform="transaction"
				)
				ctk.CTkLabel(
					self.transaction_table,
					text=name,
					font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
					text_color=GREEN,
					fg_color=SOFT_GREEN,
					anchor="center",
					justify="center",
				).grid(row=0, column=column, padx=1, pady=(0, 2), sticky="ew")
			if not rows:
				ctk.CTkLabel(
					self.transaction_table,
					text="No transactions match this search.",
					font=ctk.CTkFont(family=FONT_FAMILY, size=13),
					text_color=INK,
				).grid(row=1, column=0, columnspan=7, padx=10, pady=22, sticky="ew")
			for row_index, record in enumerate(rows):
				ticket, concern, counter, status, recipient, created, called, completed = record
				values = (
					ticket,
					f"COUNTER {counter}",
					status.upper(),
					f"{recipient or 'Not recorded'}  /  {concern or 'Legacy ticket'}",
					created.strftime("%Y-%m-%d %H:%M"),
					called.strftime("%Y-%m-%d %H:%M") if called else "-",
					completed.strftime("%Y-%m-%d %H:%M") if completed else "-",
				)
				for column, value in enumerate(values):
					cell = ctk.CTkLabel(
						self.transaction_table,
						text=value,
						font=ctk.CTkFont(family=FONT_FAMILY, size=10),
						text_color=INK,
						fg_color=SURFACE if row_index % 2 == 0 else SURFACE_ALT,
						anchor="center",
						justify="center",
						wraplength=190 if column == 3 else 125,
					)
					cell.grid(row=row_index + 1, column=column, padx=1, pady=1, sticky="nsew")
		except psycopg2.Error as error:
			self.status.set(f"Could not load transactions: {error}")

	def _build_faq_editor_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(1, weight=1)
		form = ctk.CTkFrame(
			tab,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
			corner_radius=8,
		)
		form.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
		form.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			form,
			text="FAQ EDITOR",
			font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
			text_color=GREEN,
			anchor="w",
		).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
		controls = ctk.CTkFrame(form, fg_color="transparent")
		controls.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
		self.faq_scope = tk.StringVar(value="Counter")
		counter_labels = self._counter_filter_values()[1:]
		self.faq_counter = tk.StringVar(value=counter_labels[0] if counter_labels else "No counters created")
		self.faq_target = tk.StringVar(value=counter_labels[0] if counter_labels else "No counters created")
		self.faq_target_ids: dict[str, int] = {}
		self.faq_concerns_by_counter: dict[str, dict[str, int]] = {}
		ctk.CTkOptionMenu(
			controls,
			variable=self.faq_scope,
			values=["Counter", "Concern"],
			command=lambda _value: self._on_faq_scope_changed(),
			width=150,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		).pack(side="left", padx=(0, 8))
		self.faq_counter_menu = ctk.CTkOptionMenu(
			controls,
			variable=self.faq_counter,
			values=counter_labels or ["No counters created"],
			command=lambda _value: self._on_faq_counter_changed(),
			width=150,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.faq_target_menu = ctk.CTkOptionMenu(
			controls,
			variable=self.faq_target,
			values=["COUNTER 1"],
			command=lambda _value: self._on_faq_target_changed(),
			width=280,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.faq_target_menu.pack(side="left")
		self.faq_counter_menu.pack_forget()

		ctk.CTkLabel(
			form,
			text="Question",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
		).grid(row=2, column=0, padx=14, pady=(4, 2), sticky="w")
		self.faq_question = tk.StringVar(value="")
		self.faq_question_entry = ctk.CTkEntry(
			form,
			textvariable=self.faq_question,
			placeholder_text="Enter a frequently asked question",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.faq_question_entry.grid(row=3, column=0, padx=12, pady=(0, 2), sticky="ew")
		self.faq_question_error = ctk.CTkLabel(
			form,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.faq_question_error.grid(row=4, column=0, padx=12, sticky="ew")
		ctk.CTkLabel(
			form,
			text="Answer",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
		).grid(row=5, column=0, padx=14, pady=(0, 2), sticky="w")
		self.faq_answer = ctk.CTkTextbox(
			form,
			height=86,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.faq_answer.grid(row=6, column=0, padx=12, pady=(0, 2), sticky="ew")
		self.faq_answer_error = ctk.CTkLabel(
			form,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.faq_answer_error.grid(row=7, column=0, padx=12, sticky="ew")
		buttons = ctk.CTkFrame(form, fg_color="transparent")
		buttons.grid(row=8, column=0, padx=12, pady=(0, 12), sticky="ew")
		self.faq_save_button = ctk.CTkButton(
			buttons,
			text="Add FAQ",
			command=self._save_faq_editor_entry,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		)
		self.faq_save_button.pack(side="left")
		self.faq_cancel_button = ctk.CTkButton(
			buttons,
			text="Cancel edit",
			command=self._clear_faq_editor_form,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
		)
		self.faq_cancel_button.pack(side="left", padx=8)
		self.faq_cancel_button.pack_forget()
		self.faq_editor_list = ctk.CTkScrollableFrame(
			tab,
			fg_color=ADMIN_CANVAS,
			border_width=1,
			border_color=SOFT_BORDER,
			corner_radius=8,
		)
		self.faq_editor_list.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

	def _on_faq_scope_changed(self) -> None:
		self._clear_faq_editor_form()
		self._refresh_faq_editor_targets()

	def _on_faq_target_changed(self) -> None:
		self._clear_faq_editor_form()
		self._refresh_faq_editor_list()

	def _on_faq_counter_changed(self) -> None:
		self._clear_faq_editor_form()
		self._refresh_faq_editor_targets()

	def _refresh_faq_editor_targets(self) -> None:
		try:
			counters = get_counters()
		except psycopg2.Error as error:
			self.status.set(f"Could not load FAQ counters: {error}")
			counters = []
		counter_labels = {
			format_counter_label(number, name): number
			for number, name, _prefix, _username in counters
		}
		if self.faq_scope.get() == "Counter":
			self.faq_counter_menu.pack_forget()
			self.faq_target_ids = counter_labels
		else:
			try:
				concerns = get_concerns(active_only=True)
			except psycopg2.Error as error:
				self.status.set(f"Could not load FAQ concerns: {error}")
				concerns = []
			self.faq_concerns_by_counter = {
				label: {
					f"{name} ({prefix})": concern_id
					for concern_id, name, prefix, concern_counter, _active in concerns
					if concern_counter == number
				}
				for label, number in counter_labels.items()
			}
			counter_values = list(self.faq_concerns_by_counter) or ["No counters created"]
			self.faq_counter_menu.configure(values=counter_values)
			if self.faq_counter.get() not in self.faq_concerns_by_counter:
				self.faq_counter.set(counter_values[0])
			if not self.faq_counter_menu.winfo_manager():
				self.faq_counter_menu.pack(side="left", before=self.faq_target_menu, padx=(0, 8))
			self.faq_target_ids = self.faq_concerns_by_counter.get(
				self.faq_counter.get(), {}
			)
		values = list(self.faq_target_ids) or ["No counters created" if not counters else "No active concerns"]
		self.faq_target_menu.configure(values=values)
		current = self.faq_target.get()
		self.faq_target.set(current if current in self.faq_target_ids else values[0])
		self.faq_target_menu.configure(state="normal" if self.faq_target_ids else "disabled")
		self._refresh_faq_editor_list()

	def _refresh_faq_editor_list(self) -> None:
		for child in self.faq_editor_list.winfo_children():
			child.destroy()
		target_id = self.faq_target_ids.get(self.faq_target.get())
		if target_id is None:
			return
		try:
			faqs = (
				get_faqs(counter_number=target_id)
				if self.faq_scope.get() == "Counter"
				else get_faqs(concern_id=target_id)
			)
		except psycopg2.Error as error:
			self.status.set(f"Could not load FAQs: {error}")
			return
		if not faqs:
			ctk.CTkLabel(
				self.faq_editor_list,
				text="No FAQs have been added for this selection.",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color=INK,
			).pack(padx=8, pady=12)
			return
		for faq_id, question, answer in faqs:
			row = ctk.CTkFrame(self.faq_editor_list, fg_color=SURFACE)
			row.pack(fill="x", padx=4, pady=4)
			row.grid_columnconfigure(0, weight=1)
			ctk.CTkLabel(
				row,
				text=question,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
				text_color=INK,
				anchor="w",
				wraplength=700,
			).grid(row=0, column=0, padx=10, pady=(8, 2), sticky="ew")
			ctk.CTkLabel(
				row,
				text=answer,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11),
				text_color=MUTED_TEXT,
				anchor="w",
				justify="left",
				wraplength=700,
			).grid(row=1, column=0, padx=10, pady=(0, 8), sticky="ew")
			actions = ctk.CTkFrame(row, fg_color="transparent")
			actions.grid(row=0, column=1, rowspan=2, padx=8, pady=6)
			ctk.CTkButton(
				actions,
				text="Edit",
				width=72,
				command=lambda key=faq_id, q=question, a=answer: self._edit_faq_editor_entry(key, q, a),
			).pack(pady=3)
			ctk.CTkButton(
				actions,
				text="Delete",
				width=72,
				fg_color="#A64C42",
				hover_color="#873C34",
				command=lambda key=faq_id: self._delete_faq_editor_entry(key),
			).pack(pady=3)

	def _edit_faq_editor_entry(self, faq_id: int, question: str, answer: str) -> None:
		self.faq_editor_id = faq_id
		self.faq_question.set(question)
		self.faq_answer.delete("1.0", "end")
		self.faq_answer.insert("1.0", answer)
		self._validate_faq_form(False)
		self.faq_save_button.configure(text="Save changes")
		self.faq_cancel_button.pack(side="left", padx=8)

	def _clear_faq_editor_form(self) -> None:
		self.faq_editor_id = None
		self.faq_question.set("")
		self.faq_answer.delete("1.0", "end")
		if hasattr(self, "faq_question_error"):
			self._validate_faq_form(False)
		if hasattr(self, "faq_save_button"):
			self.faq_save_button.configure(text="Add FAQ")
			self.faq_cancel_button.pack_forget()

	def _save_faq_editor_entry(self) -> None:
		if not self._validate_faq_form():
			return
		target_id = self.faq_target_ids.get(self.faq_target.get())
		if target_id is None:
			return
		try:
			faq_id = save_faq(
				self.faq_editor_id,
				self.faq_question.get(),
				self.faq_answer.get("1.0", "end-1c"),
				counter_number=target_id if self.faq_scope.get() == "Counter" else None,
				concern_id=target_id if self.faq_scope.get() == "Concern" else None,
			)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("FAQ error", str(error), parent=self)
			return
		self.status.set("FAQ saved.")
		self._clear_faq_editor_form()
		self._refresh_faq_editor_list()

	def _validate_faq_form(self, show_required: bool = True) -> bool:
		question_message = (
			"Question is required."
			if show_required and not self.faq_question.get().strip()
			else ""
		)
		set_field_error(
			self.faq_question_entry,
			self.faq_question_error,
			question_message,
		)
		answer_message = (
			"Answer is required."
			if show_required
			and not self.faq_answer.get("1.0", "end-1c").strip()
			else ""
		)
		set_field_error(self.faq_answer, self.faq_answer_error, answer_message)
		return not (question_message or answer_message)

	def _delete_faq_editor_entry(self, faq_id: int) -> None:
		if not messagebox.askyesno("Delete FAQ", "Delete this FAQ?", parent=self):
			return
		try:
			delete_faq(faq_id)
		except psycopg2.Error as error:
			messagebox.showerror("FAQ error", str(error), parent=self)
			return
		self._refresh_faq_editor_list()

	def _build_calendar_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=3, uniform="calendar")
		tab.grid_columnconfigure(1, weight=2, uniform="calendar")
		tab.grid_rowconfigure(1, weight=1)
		controls = ctk.CTkFrame(tab, fg_color="transparent")
		controls.grid(row=0, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
		ctk.CTkButton(
			controls,
			text="<",
			width=34,
			command=lambda: self._shift_calendar_month(-1),
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).pack(side="left", padx=(0, 6))
		self.calendar_month_values = list(month_calendar.month_name)[1:]
		self.calendar_month = ctk.CTkOptionMenu(
			controls,
			values=self.calendar_month_values,
			command=lambda _value: self._load_calendar(),
			width=130,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.calendar_month.set(self.calendar_month_values[self._calendar_date.month - 1])
		self.calendar_month.pack(side="left", padx=(0, 6))
		self.calendar_year_values = [str(year) for year in range(1900, 2101)]
		self.calendar_year = ctk.CTkOptionMenu(
			controls,
			values=self.calendar_year_values,
			command=lambda _value: self._load_calendar(),
			width=90,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.calendar_year.set(str(self._calendar_date.year))
		self.calendar_year.pack(side="left", padx=6)
		self.month_title = ctk.CTkLabel(
			controls,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
			text_color=INK,
		)
		self.month_title.pack(side="left", padx=14)
		self.calendar_counter = tk.StringVar(value="ALL COUNTERS")
		self.calendar_counter_menu = ctk.CTkOptionMenu(
			controls,
			variable=self.calendar_counter,
			values=self._counter_filter_values(),
			command=lambda _value: self._load_calendar(),
			width=145,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.calendar_counter_menu.pack(side="left", padx=6)
		self._counter_filter_menus.append((self.calendar_counter_menu, self.calendar_counter))
		ctk.CTkButton(
			controls,
			text=">",
			width=34,
			command=lambda: self._shift_calendar_month(1),
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).pack(side="left", padx=6)
		self.calendar_grid = ctk.CTkFrame(
			tab,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
			corner_radius=8,
		)
		self.calendar_grid.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
		self.day_panel = ctk.CTkFrame(
			tab,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
			corner_radius=8,
		)
		self.day_panel.grid(row=1, column=1, padx=8, pady=8, sticky="nsew")
		self.day_panel.grid_columnconfigure(0, weight=1)
		self.day_panel.grid_rowconfigure(1, weight=1)
		self.day_transaction_title = ctk.CTkLabel(
			self.day_panel,
			text="SELECT A DAY",
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			text_color=GREEN,
			anchor="w",
		)
		self.day_transaction_title.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")
		self.day_transactions = ctk.CTkScrollableFrame(
			self.day_panel,
			fg_color="transparent",
			corner_radius=0,
		)
		self.day_transactions.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")

	def _shift_calendar_month(self, offset: int) -> None:
		month = self.calendar_month_values.index(self.calendar_month.get()) + 1
		year = int(self.calendar_year.get())
		month_index = year * 12 + month - 1 + offset
		year, month_index = divmod(month_index, 12)
		self.calendar_month.set(self.calendar_month_values[month_index])
		self.calendar_year.set(str(year))
		self._load_calendar()

	@staticmethod
	def _set_text(widget, value: str) -> None:
		widget.configure(state="normal")
		widget.delete("1.0", "end")
		widget.insert("1.0", value)
		widget.configure(state="disabled")

	def destroy(self) -> None:
		if self._root_configure_binding_id is not None:
			try:
				self.winfo_toplevel().unbind(
					"<Configure>", self._root_configure_binding_id
				)
			except tk.TclError:
				pass
			self._root_configure_binding_id = None
		for job in (
			self._refresh_job,
			self._tab_refresh_job,
			self._section_drawer_animation_job,
			self._root_configure_job,
		):
			if job is not None:
				try:
					self.after_cancel(job)
				except tk.TclError:
					pass
		for window in (self._section_overlay, self._section_drawer_window):
			if window is not None:
				try:
					if window.winfo_exists():
						window.destroy()
				except tk.TclError:
					pass
		for job in self._queue_hover_jobs.values():
			try:
				self.after_cancel(job)
			except tk.TclError:
				pass
		super().destroy()