# COUNTER INTERFACE - COUNTER UI
# Provides the counter interface for service windows, showing queue status,
# waiting tickets, and serving controls for each counter.

import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from assets import (
center_window,
format_counter_label,
layout_responsive_grid,
set_window_icon,
)
from admin.styles import (
BORDER,
FONT_FAMILY,
GREEN,
GREEN_HOVER,
INk,
MUTED_GREEN,
PALE_GREEN,
SOFT_GREEN,
SOFT_GREEN_HOVER,
SURFACE,
SURFACE_ALT,
)
from database.queries import get_counters, get_queue_snapshot, serve_next


# class CounterControls - Counter interface frame showing queue status,
# waiting tickets, and serving controls for each counter.
class CounterControls(ctk.CTkFrame):class CounterControls(ctk.CTkFrame):
	def __init__(self, parent):
		super().__init__(parent, corner_radius=0, fg_color=PALE_GREEN)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.counter_definitions: list[tuple[int, str]] = []
		self.counter_panels: list[ctk.CTkFrame] = []
		self.current_tickets: dict[int, ctk.StringVar] = {}
		self.waiting_counts: dict[int, ctk.StringVar] = {}
		self.status = ctk.StringVar(value="Connecting to the queues...")
		self._refresh_job = None
		self._build_ui()
		self._refresh()

	def _build_ui(self) -> None:
		ctk.CTkLabel(
			self,
			text="COUNTER INTERFACE",
			font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
			text_color=INK,
			anchor="center",
		).grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
		grid = ctk.CTkScrollableFrame(self, fg_color="transparent")
		grid.grid(row=1, column=0, padx=16, pady=4, sticky="nsew")
		self.counter_grid = grid
		grid.bind("<Configure>", self._layout_counter_panels, add="+")
		self._refresh_counter_panels()
		ctk.CTkLabel(
			self,
			textvariable=self.status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="center",
		).grid(row=2, column=0, padx=24, pady=(6, 16), sticky="ew")

	def _refresh_counter_panels(self) -> None:
		try:
			counters = get_counters()
		except psycopg2.Error as error:
			self.status.set(f"Could not load counters: {error}")
			return
		definitions = [
			(number, name) for number, name, _prefix, _username in counters
		]
		if (
			definitions == self.counter_definitions
			and self.counter_grid.winfo_children()
		):
			return
		for child in self.counter_grid.winfo_children():
			child.destroy()
		self.counter_panels = []
		self.counter_grid._responsive_grid_columns = 0
		self.counter_definitions = definitions
		self.current_tickets = {
			number: ctk.StringVar(value="--") for number, _name in definitions
		}
		self.waiting_counts = {
			number: ctk.StringVar(value="Waiting: 0") for number, _name in definitions
		}
		if not definitions:
			ctk.CTkLabel(
				self.counter_grid,
				text="No counter windows are currently active.",
			).grid(row=0, column=0, padx=12, pady=12, sticky="w")
			return
		for counter_number, counter_name in definitions:
			self._build_counter(
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

	def _build_counter(
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
		ctk.CTkLabel(
			panel,
			text=format_counter_label(counter_number, counter_name),
			font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, padx=12, pady=(16, 4))
		ctk.CTkLabel(
			panel,
			text="NOW SERVING",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color=MUTED_GREEN,
		).grid(row=1, column=0, padx=12, pady=(0, 0))
		ctk.CTkLabel(
			panel,
			textvariable=self.current_tickets[counter_number],
			font=ctk.CTkFont(family=FONT_FAMILY, size=36, weight="bold"),
			text_color=INK,
		).grid(row=2, column=0, padx=12, pady=(0, 2))
		ctk.CTkLabel(
			panel,
			textvariable=self.waiting_counts[counter_number],
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
			text_color=INK,
		).grid(row=3, column=0, padx=12, pady=(0, 8))
		ctk.CTkButton(
			panel,
			text="SERVE NEXT",
			height=46,
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
			command=lambda counter=counter_number: self._serve_next(counter),
		).grid(row=4, column=0, padx=16, pady=(0, 16), sticky="ew")

	def _refresh(self) -> None:
		try:
			self._refresh_counter_panels()
			for counter_number, (serving, waiting) in get_queue_snapshot().items():
				if counter_number in self.current_tickets:
					self.current_tickets[counter_number].set(serving or "--")
					self.waiting_counts[counter_number].set(
						f"Waiting: {len(waiting)}"
					)
			self.status.set("Counter status is up to date.")
		except psycopg2.Error as error:
			self.status.set(f"Database unavailable: {error}")
		if self.winfo_exists():
			self._refresh_job = self.after(2000, self._refresh)

	def _serve_next(self, counter_number: int) -> None:
		try:
			ticket_number = serve_next(counter_number)
			counter_name = next(
				(
					name
					for number, name in self.counter_definitions
					if number == counter_number
				),
				"",
			)
			counter_label = format_counter_label(counter_number, counter_name)
			self.status.set(
				f"{ticket_number} is now serving at {counter_label}."
				if ticket_number
				else f"No waiting tickets at {counter_label}."
			)
			self._refresh()
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Queue error", str(error), parent=self)

	def destroy(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
		super().destroy()


class CounterWindow(ctk.CTkFrame):
	def __init__(
		self,
		parent,
		counter_number: int,
		counter_name: str | None = None,
		on_logout=None,
	):
		super().__init__(parent, corner_radius=0, fg_color=PALE_GREEN)
		self.counter_number = counter_number
		self.counter_name = counter_name or f"Counter {counter_number}"
		self.winfo_toplevel().title(
			f"QueueUP - {format_counter_label(counter_number, self.counter_name)}"
		)
		self.on_logout = on_logout
		self.pack(fill="both", expand=True)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(3, weight=1)
		self.status = ctk.StringVar(value="Connecting to the queue...")
		self.current_ticket = ctk.StringVar(value="--")
		self.waiting_count = ctk.StringVar(value="Waiting: 0")
		self._refresh_job = None
		self._build_ui()
		self._refresh()

	def _build_ui(self) -> None:
		header = ctk.CTkFrame(self, fg_color="transparent")
		header.grid(row=0, column=0, padx=24, pady=(18, 4), sticky="ew")
		header.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			header,
			text=format_counter_label(self.counter_number, self.counter_name),
			font=ctk.CTkFont(family=FONT_FAMILY, size=32, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, sticky="w")
		if self.on_logout is not None:
			ctk.CTkButton(
				header,
				text="Log Out",
				width=100,
				command=self.on_logout,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				fg_color=SOFT_GREEN,
				hover_color=SOFT_GREEN_HOVER,
				text_color=INK,
			).grid(row=0, column=1, sticky="e")
		ctk.CTkLabel(self, text="NOW SERVING", font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"), text_color=GREEN).grid(
			row=1, column=0, padx=20, pady=(8, 0)
		)
		ctk.CTkLabel(
			self,
			textvariable=self.current_ticket,
			font=ctk.CTkFont(family=FONT_FAMILY, size=68, weight="bold"),
			text_color=INK,
		).grid(row=2, column=0, padx=20, pady=(0, 8))
		queue_panel = ctk.CTkFrame(
			self,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
		)
		queue_panel.grid(row=3, column=0, padx=32, pady=12, sticky="nsew")
		queue_panel.grid_columnconfigure(0, weight=1)
		queue_panel.grid_rowconfigure(1, weight=1)
		ctk.CTkLabel(
			queue_panel,
			textvariable=self.waiting_count,
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
		).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")
		self.queue_text = ctk.CTkTextbox(
			queue_panel,
			activate_scrollbars=True,
			fg_color=SURFACE_ALT,
			border_color=BORDER,
			text_color=INK,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.queue_text.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="nsew")
		self.queue_text.configure(state="disabled")
		ctk.CTkButton(
			self,
			text="SERVE NEXT",
			width=220,
			height=52,
			font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
			command=self._serve_next,
		).grid(row=4, column=0, padx=24, pady=(8, 4))
		ctk.CTkLabel(
			self,
			textvariable=self.status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="center",
		).grid(
			row=5, column=0, padx=20, pady=(4, 18)
		)

	def _refresh(self) -> None:
		try:
			queue = get_queue_snapshot().get(self.counter_number)
			if queue is None:
				self.status.set("This counter is no longer active. Please log out.")
				self.current_ticket.set("--")
				self.waiting_count.set("Waiting: 0")
				self.queue_text.configure(state="normal")
				self.queue_text.delete("1.0", "end")
				self.queue_text.insert("1.0", "Counter is no longer active.")
				self.queue_text.configure(state="disabled")
				self._refresh_job = self.after(2000, self._refresh)
				return
			serving, waiting = queue
			self.current_ticket.set(serving or "--")
			self.waiting_count.set(f"Waiting: {len(waiting)}")
			self.queue_text.configure(state="normal")
			self.queue_text.delete("1.0", "end")
			self.queue_text.insert(
				"1.0",
				"\n".join(f"{position}.  {ticket}" for position, ticket in enumerate(waiting, 1))
				or "No waiting tickets",
			)
			self.queue_text.configure(state="disabled")
			self.status.set("Queue is up to date.")
		except psycopg2.Error as error:
			self.status.set(f"Database unavailable: {error}")
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
		self._refresh_job = self.after(2000, self._refresh)

	def _serve_next(self) -> None:
		try:
			ticket_number = serve_next(self.counter_number)
			self.status.set(
				f"{ticket_number} is now being served."
				if ticket_number
				else "There are no waiting tickets."
			)
			self._refresh()
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Queue error", str(error), parent=self)

	def destroy(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
			self._refresh_job = None
		super().destroy()


def main(counter_number: int = 1) -> None:
	root = ctk.CTk()
	root.title(f"QueueUP - Counter {counter_number}")
	set_window_icon(root)
	root.configure(fg_color=PALE_GREEN)
	root.geometry("700x600")
	root.minsize(540, 480)
	center_window(root)
	CounterWindow(root, counter_number)
	root.mainloop()
