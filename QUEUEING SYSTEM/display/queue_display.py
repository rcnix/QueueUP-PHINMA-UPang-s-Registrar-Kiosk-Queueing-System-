"""Display-only queue board for the waiting-area television.

The board is a pure display surface: it never asks for a ticket number and
never performs a lookup. It renders the live state of every active counter so
recipients watching the television can see which counter is serving them,
what is being served right now, and who is up next.

The layout is tuned for a television that is viewed from a distance, so the
serving ticket is rendered far larger than everything else and the counters
are laid out in a responsive grid that reflows as the window is resized.
"""
# DISPLAY QUEUE BOARD - DISPLAY UI
# Provides a television-facing display of live queue status for all counters,
# showing the current serving ticket, waiting list, and updated information.

from datetime import datetime


import tkinter as tk
from datetime import datetime

import customtkinter as ctk
import psycopg2

from admin.styles import (
	BORDER,
	FONT_FAMILY,
	GREEN,
	INK,
	MUTED_GREEN,
	MUTED_TEXT,
	PALE_GREEN,
	SOFT_GREEN,
	SURFACE,
)
from assets import (
	format_counter_label,
	layout_responsive_grid,
	set_window_icon,
)
from database.queries import get_recipient_queue_board


REFRESH_INTERVAL_MS = 1500

HEADER_FONT_SIZE = 30
COUNTER_TITLE_SIZE = 20
SERVING_SIZE = 64
NEXT_SIZE = 30
QUEUE_SIZE = 15


class QueueBoardWindow(ctk.CTkToplevel):
	"""A television-friendly board showing the live state of every counter."""

	def __init__(self, master=None):
		super().__init__(master=master)
		self.title("QueueUP - Queue Display")
		set_window_icon(self)
		self.geometry("1280x720")
		self.minsize(900, 540)
		self.protocol("WM_DELETE_WINDOW", self._on_close)

		self.status = tk.StringVar(master=self, value="Connecting to the queue service...")
		self.clock = tk.StringVar(master=self, value="--:--")
		self.summary = tk.StringVar(master=self, value="")
		self.now_serving: dict[int, tk.StringVar] = {}
		self.up_next: dict[int, tk.StringVar] = {}
		self.queue_text: dict[int, tk.StringVar] = {}
		self.waiting_badges: dict[int, ctk.CTkLabel] = {}
		self.counter_panels: list[ctk.CTkFrame] = []
		self.counter_definitions: list[tuple[int, str]] = []
		self._refresh_job = None

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self._build_ui()
		self._refresh()



	# ------------------------------------------------------------------
	# Layout
	# ------------------------------------------------------------------
	def _build_ui(self) -> None:
		header = ctk.CTkFrame(self, fg_color="transparent")
		header.grid(row=0, column=0, padx=24, pady=(18, 6), sticky="ew")
		header.grid_columnconfigure(1, weight=1)

		ctk.CTkLabel(
			header,
			text="NOW SERVING",
			font=ctk.CTkFont(family=FONT_FAMILY, size=HEADER_FONT_SIZE, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=0, column=0, rowspan=2, sticky="w")

		ctk.CTkLabel(
			header,
			textvariable=self.summary,
			font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
			text_color=GREEN,
			anchor="e",
		).grid(row=0, column=1, sticky="e")

		ctk.CTkLabel(
			header,
			textvariable=self.clock,
			font=ctk.CTkFont(family=FONT_FAMILY, size=17),
			text_color=MUTED_TEXT,
			anchor="e",
		).grid(row=1, column=1, sticky="e")

		self.board = ctk.CTkScrollableFrame(
			self,
			fg_color="transparent",
			corner_radius=0,
		)
		self.board.grid(row=1, column=0, padx=18, pady=4, sticky="nsew")
		self.board.bind("<Configure>", self._layout_counter_panels, add="+")

		ctk.CTkLabel(
			self,
			textvariable=self.status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
			text_color=MUTED_TEXT,
		).grid(row=2, column=0, padx=20, pady=(4, 12))


	# ------------------------------------------------------------------
	# Counter panels
	# ------------------------------------------------------------------
	def _render_counters(self, board_data: list[dict]) -> None:
		for child in self.board.winfo_children():
			child.destroy()
		self.counter_panels = []
		self.board._responsive_grid_columns = 0
		self.waiting_badges = {}

		self.counter_definitions = [
			(entry["counter_number"], entry["counter_label"])
			for entry in board_data
		]
		self.now_serving = {
			entry["counter_number"]: tk.StringVar(master=self, value="--")
			for entry in board_data
		}
		self.up_next = {
			entry["counter_number"]: tk.StringVar(master=self, value="--")
			for entry in board_data
		}
		self.queue_text = {
			entry["counter_number"]: tk.StringVar(master=self, value="")
			for entry in board_data
		}

		if not board_data:
			ctk.CTkLabel(
				self.board,
				text="No counters are active right now.",
				font=ctk.CTkFont(family=FONT_FAMILY, size=20),
				text_color=MUTED_TEXT,
			).grid(row=0, column=0, padx=12, pady=24, sticky="w")
			return

		for entry in board_data:
			counter_number = entry["counter_number"]
			panel = ctk.CTkFrame(
				self.board,
				fg_color=SURFACE,
				corner_radius=10,
				border_width=1,
				border_color=BORDER,
			)
			self.counter_panels.append(panel)
			panel.grid_columnconfigure(0, weight=1)
			panel.grid_rowconfigure(4, weight=1)

			ctk.CTkLabel(
				panel,
				text=entry["counter_label"],
				font=ctk.CTkFont(family=FONT_FAMILY, size=COUNTER_TITLE_SIZE, weight="bold"),
				text_color=INK,
				anchor="w",
			).grid(row=0, column=0, padx=16, pady=(14, 2), sticky="ew")

			self.waiting_badges[counter_number] = ctk.CTkLabel(
				panel,
				text="",
				fg_color=SOFT_GREEN,
				corner_radius=6,
				text_color=INK,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
				width=88,
			)
			self.waiting_badges[counter_number].grid(
				row=0, column=1, padx=(0, 16), pady=(14, 2), sticky="e"
			)

			ctk.CTkLabel(
				panel,
				text="NOW SERVING",
				font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
				text_color=MUTED_GREEN,
				anchor="w",
			).grid(row=1, column=0, padx=16, pady=(6, 0), sticky="ew")

			ctk.CTkLabel(
				panel,
				textvariable=self.now_serving[counter_number],
				font=ctk.CTkFont(family=FONT_FAMILY, size=SERVING_SIZE, weight="bold"),
				text_color=GREEN,
				anchor="w",
			).grid(row=2, column=0, padx=16, pady=(0, 4), sticky="ew")

			ctk.CTkLabel(
				panel,
				text="UP NEXT",
				font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
				text_color=MUTED_GREEN,
				anchor="w",
			).grid(row=3, column=0, padx=16, pady=(6, 0), sticky="ew")

			ctk.CTkLabel(
				panel,
				textvariable=self.up_next[counter_number],
				font=ctk.CTkFont(family=FONT_FAMILY, size=NEXT_SIZE, weight="bold"),
				text_color=INK,
				anchor="w",
			).grid(row=4, column=0, padx=16, pady=(0, 6), sticky="ew")

			ctk.CTkLabel(
				panel,
				textvariable=self.queue_text[counter_number],
				font=ctk.CTkFont(family=FONT_FAMILY, size=QUEUE_SIZE),
				text_color=MUTED_TEXT,
				anchor="nw",
				justify="left",
			).grid(row=5, column=0, padx=16, pady=(0, 14), sticky="new")

		self._layout_counter_panels()


	def _layout_counter_panels(self, _event=None) -> None:
		if not self.counter_panels:
			return
		width = self.board._parent_frame.winfo_width()
		if width <= 1:
			return
		layout_responsive_grid(
			self.board,
			self.counter_panels,
			width,
			minimum_item_width=380,
			max_columns=3,
		)

	# ------------------------------------------------------------------
	# Live refresh
	# ------------------------------------------------------------------
	def _update_counters(self, board_data: list[dict]) -> None:
		for entry in board_data:
			counter_number = entry["counter_number"]
			if counter_number not in self.now_serving:
				continue
			waiting = entry["waiting"]
			self.now_serving[counter_number].set(entry["now_serving"] or "--")
			self.up_next[counter_number].set(waiting[0] if waiting else "--")
			badge = self.waiting_badges.get(counter_number)
			if badge is not None:
				badge.configure(text=f"{entry['waiting_count']} WAITING")
			if waiting:
				self.queue_text[counter_number].set(
					"WAITING  "
					+ "   ".join(str(ticket) for ticket in waiting[:6])
				)
			else:
				self.queue_text[counter_number].set("NO ONE WAITING")

		waiting_total = sum(entry["waiting_count"] for entry in board_data)
		counter_label = "COUNTER" if len(board_data) == 1 else "COUNTERS"
		self.summary.set(
			f"{len(board_data)} {counter_label}  |  {waiting_total} WAITING"
		)

	def _refresh(self) -> None:
		try:
			board_data = get_recipient_queue_board()
			for entry in board_data:
				entry["counter_label"] = format_counter_label(
					entry["counter_number"], entry["counter_name"]
				)
			definitions = [
				(entry["counter_number"], entry["counter_label"])
				for entry in board_data
			]
			if definitions != self.counter_definitions:
				self._render_counters(board_data)
			self._update_counters(board_data)
			self.clock.set(datetime.now().strftime("%I:%M:%S %p").lstrip("0"))
			self.status.set("Live queue status")
		except psycopg2.Error as error:
			self.status.set(f"Queue service unavailable: {error}")
		self._schedule_refresh()

	def _schedule_refresh(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
		self._refresh_job = self.after(REFRESH_INTERVAL_MS, self._refresh)

	def _on_close(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
			self._refresh_job = None
		self.destroy()


def open_queue_board(master=None) -> QueueBoardWindow:
	"""Open (or raise) the television queue board window."""
	return QueueBoardWindow(master)


def main() -> None:
	ctk.set_appearance_mode("Light")
	ctk.set_default_color_theme("green")
	ctk.ThemeManager.theme["CTkFont"]["family"] = FONT_FAMILY
	root = ctk.CTk(fg_color=PALE_GREEN)
	root.withdraw()
	window = QueueBoardWindow(root)
	window.mainloop()
