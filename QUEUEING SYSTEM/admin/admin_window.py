# ADMIN LIVE DASHBOARD - ADMIN UI
# Provides a real-time counter display showing queue status, active tickets,
# and live updates for the admin dashboard view.

import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from admin.styles import (
BORDER,
FONT_FAMILY,
GREEN,
INK,
MUTED_GREEN,
PALE_GREEN,
SURFACE,
)
from assets import (
center_window,
format_counter_label,
layout_responsive_grid,
set_window_icon,
)
from database.queries import ensure_schema, get_counters, get_queue_snapshot


# class MainFrame - Main frame for the admin live dashboard, showing live
# counter activity, queue snapshots, and responsive counter panels.
class MainFrame(ctk.CTkFrame):
	def __init__(self, parent):
		super().__init__(parent, corner_radius=0, fg_color=PALE_GREEN)
		self.root = self.winfo_toplevel()
		self.pack(fill="both", expand=True)
		self.counter_definitions: list[tuple[int, str]] = []
		self.counter_panels: list[ctk.CTkFrame] = []
		self.current_tickets: dict[int, tk.StringVar] = {}
		self.status = tk.StringVar(value="Live counter activity is being updated in real time.")
		self._refresh_job = None
		self._build_dashboard()
		self._refresh_queues()

	def _build_dashboard(self) -> None:
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		header = ctk.CTkFrame(self, fg_color="transparent")
		header.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
		header.grid_columnconfigure(0, weight=1)
		header.grid_columnconfigure(1, weight=1)
		ctk.CTkLabel(
			header,
			text="LIVE COUNTER",
			font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
			text_color=INK,
			anchor="center",
		).grid(row=0, column=0, columnspan=2, sticky="ew")
		ctk.CTkLabel(
			header,
			text="Live Counter Display for QueueUP",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color=GREEN,
			anchor="center",
		).grid(row=1, column=0, columnspan=2, pady=(2, 0), sticky="ew")

		counter_grid = ctk.CTkScrollableFrame(self, fg_color="transparent")
		counter_grid.grid(row=1, column=0, padx=16, pady=6, sticky="nsew")
		self.counter_grid = counter_grid
		counter_grid.bind(
			"<Configure>", self._layout_counter_panels, add="+"
		)
		self._render_counter_panels([])

		ctk.CTkLabel(
			self,
			textvariable=self.status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="center",
		).grid(row=2, column=0, padx=24, pady=(6, 16), sticky="ew")

	def _render_counter_panels(self, counters: list[tuple[int, str, str, str]]) -> None:
		for child in self.counter_grid.winfo_children():
			child.destroy()
		self.counter_panels = []
		self.counter_grid._responsive_grid_columns = 0
		self.counter_definitions = [
			(number, name) for number, name, _prefix, _username in counters
		]
		self.current_tickets = {
			number: tk.StringVar(value="--") for number, _name in self.counter_definitions
		}
		if not self.counter_definitions:
			ctk.CTkLabel(
				self.counter_grid,
				text="No counter windows are currently active.",
			).grid(row=0, column=0, padx=12, pady=12, sticky="w")
			return
		for counter_number, counter_name in self.counter_definitions:
			self._build_counter_panel(
				self.counter_grid, counter_number, counter_name
			)
		self._layout_counter_panels()

	def _layout_counter_panels(self, _event=None) -> None:
		if not self.counter_panels:
			return
		width = self.counter_grid._parent_frame.winfo_width()
		if width <= 1:
			return
		layout_responsive_grid(
			self.counter_grid,
			self.counter_panels,
			width,
			minimum_item_width=300,
		)

	def _build_counter_panel(
		self,
		parent,
		counter_number: int,
		counter_name: str,
	) -> None:
		panel = ctk.CTkFrame(
			parent,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
			corner_radius=8,
		)
		self.counter_panels.append(panel)
		panel.grid_columnconfigure(0, weight=1)
		panel.grid_rowconfigure(2, weight=1)
		ctk.CTkLabel(
			panel,
			text=format_counter_label(counter_number, counter_name),
			font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, padx=12, pady=(16, 2))
		ctk.CTkLabel(
			panel,
			text="NOW SERVING",
			font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
			text_color=MUTED_GREEN,
		).grid(row=1, column=0, padx=12, pady=(4, 0))
		ctk.CTkLabel(
			panel,
			textvariable=self.current_tickets[counter_number],
			font=ctk.CTkFont(family=FONT_FAMILY, size=44, weight="bold"),
			text_color=INK,
		).grid(row=2, column=0, padx=12, pady=(0, 18), sticky="nsew")

	def _refresh_queues(self) -> None:
		try:
			counters = get_counters()
			definitions = [
				(number, name) for number, name, _prefix, _username in counters
			]
			if definitions != self.counter_definitions:
				self._render_counter_panels(counters)
			snapshot = get_queue_snapshot()
			for counter_number, (serving, _waiting) in snapshot.items():
				if counter_number in self.current_tickets:
					self.current_tickets[counter_number].set(serving or "--")
			self.status.set("Live counter activity is being updated in real time.")
		except psycopg2.Error as error:
			self.status.set(f"Could not refresh counters: {error}")
		if self.winfo_exists():
			self._refresh_job = self.after(2000, self._refresh_queues)

	def destroy(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
		super().destroy()


def main(prepare_schema: bool = True) -> None:
	ctk.set_appearance_mode("Light")
	ctk.set_default_color_theme("green")
	ctk.ThemeManager.theme["CTkFont"]["family"] = FONT_FAMILY
	if prepare_schema:
		try:
			ensure_schema()
		except psycopg2.Error as error:
			root = ctk.CTk()
			root.withdraw()
			messagebox.showerror(
				"Database setup error",
				"Could not prepare the PostgreSQL database.\n\n"
				f"{error}\n\n"
				"Check that PostgreSQL is running and that .env has the "
				"correct database, username, password, host, and port!",
				parent=root,
			)
			root.destroy()
			return
	from application import QueueUPApp
	root = QueueUPApp()
	root.mainloop()


if __name__ == "__main__":
	main()