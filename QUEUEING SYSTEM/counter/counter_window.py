import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from assets import set_window_icon
from database.queries import get_queue_snapshot, serve_next


FONT_FAMILY = "Bahnschrift"
GREEN = "#397A45"
GREEN_HOVER = "#2F6639"
PALE_GREEN = "#E8F3E8"
INK = "#183B22"


class CounterControls(ctk.CTkFrame):
	COUNTER_COUNT = 6

	def __init__(self, parent):
		super().__init__(parent, corner_radius=0, fg_color=PALE_GREEN)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.current_tickets = [
			ctk.StringVar(value="--") for _ in range(self.COUNTER_COUNT)
		]
		self.waiting_counts = [
			ctk.StringVar(value="Waiting: 0") for _ in range(self.COUNTER_COUNT)
		]
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
		grid = ctk.CTkFrame(self, fg_color="transparent")
		grid.grid(row=1, column=0, padx=16, pady=4, sticky="nsew")
		for row in range(2):
			grid.grid_rowconfigure(row, weight=1, uniform="counter-row")
		for column in range(3):
			grid.grid_columnconfigure(column, weight=1, uniform="counter-column")
		for index in range(self.COUNTER_COUNT):
			self._build_counter(grid, index)
		ctk.CTkLabel(
			self,
			textvariable=self.status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="center",
		).grid(row=2, column=0, padx=24, pady=(6, 16), sticky="ew")

	def _build_counter(self, parent, index: int) -> None:
		panel = ctk.CTkFrame(
			parent,
			fg_color="#F7FBF6",
			border_width=1,
			border_color="#BCD5BE",
			corner_radius=8,
		)
		panel.grid(
			row=index // 3,
			column=index % 3,
			padx=10,
			pady=10,
			sticky="nsew",
		)
		panel.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			panel,
			text=f"COUNTER {index + 1}",
			font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, padx=12, pady=(16, 4))
		ctk.CTkLabel(
			panel,
			text="NOW SERVING",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color="#52765A",
		).grid(row=1, column=0, padx=12, pady=(0, 0))
		ctk.CTkLabel(
			panel,
			textvariable=self.current_tickets[index],
			font=ctk.CTkFont(family=FONT_FAMILY, size=36, weight="bold"),
			text_color=INK,
		).grid(row=2, column=0, padx=12, pady=(0, 2))
		ctk.CTkLabel(
			panel,
			textvariable=self.waiting_counts[index],
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
			command=lambda counter=index + 1: self._serve_next(counter),
		).grid(row=4, column=0, padx=16, pady=(0, 16), sticky="ew")

	def _refresh(self) -> None:
		try:
			for counter_number, (serving, waiting) in get_queue_snapshot().items():
				self.current_tickets[counter_number - 1].set(serving or "--")
				self.waiting_counts[counter_number - 1].set(f"Waiting: {len(waiting)}")
			self.status.set("Counter status is up to date.")
		except psycopg2.Error as error:
			self.status.set(f"Database unavailable: {error}")
		if self.winfo_exists():
			self._refresh_job = self.after(2000, self._refresh)

	def _serve_next(self, counter_number: int) -> None:
		try:
			ticket_number = serve_next(counter_number)
			self.status.set(
				f"{ticket_number} is now serving at COUNTER {counter_number}."
				if ticket_number
				else f"No waiting tickets at COUNTER {counter_number}."
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


class CounterWindow(ctk.CTk):
	def __init__(self, counter_number: int = 1):
		super().__init__()
		self.counter_number = counter_number
		self.title(f"QueueUP - Counter {counter_number}")
		set_window_icon(self)
		self.configure(fg_color=PALE_GREEN)
		self.geometry("700x600")
		self.minsize(540, 480)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(3, weight=1)
		self.status = ctk.StringVar(value="Connecting to the queue...")
		self.current_ticket = ctk.StringVar(value="--")
		self.waiting_count = ctk.StringVar(value="Waiting: 0")
		self._refresh_job = None
		self._build_ui()
		self._refresh()

	def _build_ui(self) -> None:
		ctk.CTkLabel(
			self,
			text=f"COUNTER {self.counter_number}",
			font=ctk.CTkFont(family=FONT_FAMILY, size=32, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, padx=24, pady=(24, 8))
		ctk.CTkLabel(self, text="NOW SERVING", font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"), text_color=GREEN).grid(
			row=1, column=0, padx=20, pady=(14, 0)
		)
		ctk.CTkLabel(
			self,
			textvariable=self.current_ticket,
			font=ctk.CTkFont(family=FONT_FAMILY, size=68, weight="bold"),
			text_color=INK,
		).grid(row=2, column=0, padx=20, pady=(0, 8))
		queue_panel = ctk.CTkFrame(self)
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
			serving, waiting = get_queue_snapshot()[self.counter_number]
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


def main(counter_number: int = 1) -> None:
	CounterWindow(counter_number).mainloop()
