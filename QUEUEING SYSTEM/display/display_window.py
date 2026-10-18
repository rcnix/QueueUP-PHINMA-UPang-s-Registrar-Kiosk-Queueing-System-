import customtkinter as ctk
import psycopg2

from admin.styles import BORDER, PALE_GREEN, SURFACE
from assets import (
	center_window,
	format_counter_label,
	layout_responsive_grid,
	set_window_icon,
)
from database.queries import get_counters, get_queue_snapshot


class DisplayWindow(ctk.CTk):
	def __init__(self):
		super().__init__(fg_color=PALE_GREEN)
		self.title("QueueUP - Queue Display")
		set_window_icon(self)
		self.geometry("1280x720")
		self.minsize(800, 480)
		center_window(self)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.status = ctk.StringVar(value="Connecting to queue service...")
		self.counter_definitions: list[tuple[int, str]] = []
		self.counter_panels: list[ctk.CTkFrame] = []
		self.now_serving: dict[int, ctk.StringVar] = {}
		self.up_next: dict[int, ctk.StringVar] = {}
		self._build_ui()
		self._refresh()

	def _build_ui(self) -> None:
		ctk.CTkLabel(
			self,
			text="QUEUEUP  /  NOW SERVING",
			font=ctk.CTkFont(size=26, weight="bold"),
		).grid(row=0, column=0, padx=30, pady=(24, 12))
		board = ctk.CTkScrollableFrame(
			self,
			fg_color="transparent",
			corner_radius=0,
		)
		board.grid(row=1, column=0, padx=24, pady=8, sticky="nsew")
		self.board = board
		board.bind("<Configure>", self._layout_counter_panels, add="+")
		self._render_counters([])
		ctk.CTkLabel(self, textvariable=self.status).grid(
			row=2, column=0, padx=20, pady=(6, 14)
		)

	def _render_counters(self, counters: list[tuple[int, str, str, str]]) -> None:
		for child in self.board.winfo_children():
			child.destroy()
		self.counter_panels = []
		self.board._responsive_grid_columns = 0
		self.counter_definitions = [
			(counter_number, name)
			for counter_number, name, _prefix, _username in counters
		]
		self.now_serving = {
			counter_number: ctk.StringVar(value="--")
			for counter_number, _name in self.counter_definitions
		}
		self.up_next = {
			counter_number: ctk.StringVar(value="--")
			for counter_number, _name in self.counter_definitions
		}
		if not self.counter_definitions:
			ctk.CTkLabel(
				self.board,
				text="No counter windows are currently active.",
			).grid(row=0, column=0, padx=12, pady=16, sticky="w")
			return
		for counter_number, counter_name in self.counter_definitions:
			panel = ctk.CTkFrame(
				self.board,
				fg_color=SURFACE,
				border_width=1,
				border_color=BORDER,
			)
			self.counter_panels.append(panel)
			panel.grid_columnconfigure(0, weight=1)
			ctk.CTkLabel(
				panel,
				text=format_counter_label(counter_number, counter_name),
				font=ctk.CTkFont(size=17, weight="bold"),
			).grid(row=0, column=0, padx=12, pady=(18, 10))
			ctk.CTkLabel(panel, text="NOW SERVING", font=ctk.CTkFont(size=12)).grid(
				row=1, column=0, padx=12, pady=(4, 0)
			)
			ctk.CTkLabel(
				panel,
				textvariable=self.now_serving[counter_number],
				font=ctk.CTkFont(size=38, weight="bold"),
			).grid(row=2, column=0, padx=12, pady=(0, 10))
			ctk.CTkLabel(panel, text="UP NEXT", font=ctk.CTkFont(size=12)).grid(
				row=3, column=0, padx=12, pady=(4, 0)
			)
			ctk.CTkLabel(
				panel,
				textvariable=self.up_next[counter_number],
				font=ctk.CTkFont(size=24, weight="bold"),
			).grid(row=4, column=0, padx=12, pady=(0, 18))
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
			minimum_item_width=300,
		)

	def _refresh(self) -> None:
		try:
			counters = get_counters()
			definitions = [
				(counter_number, name)
				for counter_number, name, _prefix, _username in counters
			]
			if definitions != self.counter_definitions:
				self._render_counters(counters)
			snapshot = get_queue_snapshot()
			for counter_number in self.now_serving:
				serving, waiting = snapshot.get(counter_number, (None, []))
				self.now_serving[counter_number].set(serving or "--")
				self.up_next[counter_number].set(waiting[0] if waiting else "--")
			self.status.set("Live queue status")
		except psycopg2.Error as error:
			self.status.set(f"Queue service unavailable: {error}")
		self.after(1500, self._refresh)


def main() -> None:
	DisplayWindow().mainloop()
