import tkinter as tk
from datetime import datetime

import customtkinter as ctk
import psycopg2

from admin.styles import (
	BORDER,
	FONT_FAMILY,
	GREEN,
	GREEN_HOVER,
	INK,
	MUTED_GREEN,
	MUTED_TEXT,
	PALE_BORDER,
	SOFT_GREEN,
	SOFT_GREEN_HOVER,
	SURFACE,
	SURFACE_ALT,
)
from assets import format_counter_label, set_window_icon
from database.queries import (
	get_recipient_faqs_for_ticket,
	get_recipient_queue_board,
	get_recipient_ticket,
)


STATUS_LABELS = {
	"waiting": "WAITING IN QUEUE",
	"serving": "NOW BEING SERVED",
	"completed": "COMPLETED",
	"cancelled": "CANCELLED",
}

REFRESH_INTERVAL_MS = 2000

DETAIL_KEYS = (
	"Recipient",
	"Service",
	"Counter",
	"Your Position",
	"Estimated Wait",
)


def format_duration(seconds: float) -> str:
	"""Render a wait estimate as a short human readable duration."""
	minutes = int(round(seconds / 60))
	if minutes < 1:
		return "Less than a minute"
	if minutes < 60:
		return f"About {minutes} minute{'s' if minutes != 1 else ''}"
	hours, _remainder = divmod(minutes, 60)
	if hours < 24:
		return f"About {hours} hour{'s' if hours != 1 else ''}"
	return f"About {hours // 24} day{'s' if hours // 24 != 1 else ''}"


def format_clock(value: datetime | None) -> str:
	"""Render a timestamp as a short clock time."""
	if value is None:
		return "--"
	return value.strftime("%I:%M %p").lstrip("0")


class RecipientSimulationWindow(ctk.CTkToplevel):
	"""A recipient-facing view of the live queues."""

	def __init__(self, master=None):
		super().__init__(master=master)
		self.title("QueueUP - Counter Simulation")
		set_window_icon(self)
		self.geometry("1180x760")
		self.minsize(940, 640)
		self.transient(master)
		self.protocol("WM_DELETE_WINDOW", self._on_close)

		self.status = tk.StringVar(value="Enter your ticket number to track your place in line.")
		self.lookup_feedback = tk.StringVar(value="")
		self.ticket_number = tk.StringVar(value="")
		self.selected_counter = tk.StringVar(value="Select a counter")
		self.ticket: dict | None = None
		self.counter_view: dict | None = None
		self.board_data: list[dict] = []
		self._board_key: tuple = ()
		self._refresh_job = None
		self._counter_panels: dict[int, dict] = {}

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self._build_lookup_bar()
		self._build_body()
		self._refresh()

	# ------------------------------------------------------------------
	# Layout
	# ------------------------------------------------------------------
	def _build_lookup_bar(self) -> None:
		bar = ctk.CTkFrame(
			self,
			fg_color=SURFACE,
			corner_radius=10,
			border_width=1,
			border_color=BORDER,
		)
		bar.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
		bar.grid_columnconfigure(1, weight=1)

		ctk.CTkLabel(
			bar,
			text="COUNTER SIMULATION",
			font=ctk.CTkFont(family=FONT_FAMILY, size=19, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, padx=(18, 14), pady=(12, 0), sticky="w")
		ctk.CTkLabel(
			bar,
			text="See your place in line, what is served now, and who is up next.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=MUTED_TEXT,
		).grid(row=1, column=0, padx=(18, 14), pady=(0, 12), sticky="w")

		controls = ctk.CTkFrame(bar, fg_color="transparent")
		controls.grid(row=0, column=1, rowspan=2, padx=(0, 18), pady=12, sticky="e")
		controls.grid_columnconfigure(0, weight=1)

		entry = ctk.CTkEntry(
			controls,
			textvariable=self.ticket_number,
			width=210,
			height=40,
			placeholder_text="Ticket number",
			font=ctk.CTkFont(family=FONT_FAMILY, size=14),
		)
		entry.grid(row=0, column=0, padx=(0, 10), sticky="w")
		entry.bind("<Return>", lambda _event: self._lookup_ticket())

		ctk.CTkButton(
			controls,
			text="CHECK MY QUEUE",
			command=self._lookup_ticket,
			width=165,
			height=40,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=0, column=1, padx=(0, 10))
		ctk.CTkButton(
			controls,
			text="CLEAR",
			command=self._clear_ticket,
			width=88,
			height=40,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
		).grid(row=0, column=2)

		ctk.CTkLabel(
			controls,
			text="or",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=MUTED_TEXT,
		).grid(row=0, column=3, padx=(0, 10))
		self.counter_choice = ctk.CTkOptionMenu(
			controls,
			variable=self.selected_counter,
			values=["Select a counter"],
			command=self._lookup_counter,
			width=210,
			height=40,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13),
			fg_color=SURFACE_ALT,
			button_color=SOFT_GREEN,
			button_hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
			dropdown_fg_color=SURFACE_ALT,
			dropdown_hover_color=SOFT_GREEN_HOVER,
			dropdown_text_color=INK,
		)
		self.counter_choice.grid(row=0, column=4, padx=(0, 10))
		ctk.CTkButton(
			controls,
			text="VIEW COUNTER",
			command=self._lookup_counter,
			width=140,
			height=40,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=0, column=5)

	def _build_body(self) -> None:
		body = ctk.CTkFrame(self, fg_color="transparent")
		body.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="nsew")
		body.grid_columnconfigure(0, weight=0, minsize=340)
		body.grid_columnconfigure(1, weight=1)
		body.grid_rowconfigure(0, weight=1)

		self._build_ticket_panel(body)

		right = ctk.CTkFrame(body, fg_color="transparent")
		right.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
		right.grid_columnconfigure(0, weight=1)
		right.grid_rowconfigure(1, weight=1)

		counter_bar = ctk.CTkFrame(right, fg_color="transparent")
		counter_bar.grid(row=0, column=0, pady=(0, 8), sticky="ew")
		counter_bar.grid_columnconfigure(1, weight=1)
		ctk.CTkLabel(
			counter_bar,
			text="LIVE COUNTERS",
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, sticky="w")
		ctk.CTkLabel(
			counter_bar,
			textvariable=self.status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=MUTED_TEXT,
			anchor="e",
		).grid(row=0, column=1, sticky="e")

		self.board = ctk.CTkScrollableFrame(right, fg_color="transparent")
		self.board.grid(row=1, column=0, sticky="nsew")
		self.board.bind("<Configure>", self._layout_counter_panels, add="+")
		self.counter_grid = ctk.CTkFrame(self.board, fg_color="transparent")
		self.counter_grid.grid(row=0, column=0, sticky="nsew")
		self.counter_grid.grid_columnconfigure(0, weight=1)

	def _build_ticket_panel(self, parent) -> None:
		panel = ctk.CTkFrame(
			parent,
			fg_color=SURFACE,
			corner_radius=10,
			border_width=1,
			border_color=BORDER,
		)
		panel.grid(row=0, column=0, sticky="nsew")
		panel.grid_columnconfigure(0, weight=1)

		ctk.CTkLabel(
			panel,
			text="MY TICKET",
			font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=0, column=0, padx=16, pady=(14, 2), sticky="ew")
		ctk.CTkLabel(
			panel,
			textvariable=self.lookup_feedback,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=MUTED_TEXT,
			anchor="w",
			wraplength=290,
			justify="left",
		).grid(row=1, column=0, padx=16, pady=(0, 8), sticky="ew")

		self.ticket_heading = ctk.CTkLabel(
			panel,
			text="--",
			font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
			text_color=GREEN,
			anchor="w",
		)
		self.ticket_heading.grid(row=2, column=0, padx=16, sticky="ew")
		self.ticket_status = ctk.CTkLabel(
			panel,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=MUTED_GREEN,
			anchor="w",
		)
		self.ticket_status.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="ew")

		details = ctk.CTkFrame(
			panel,
			fg_color=SURFACE_ALT,
			corner_radius=8,
			border_width=1,
			border_color=PALE_BORDER,
		)
		details.grid(row=4, column=0, padx=12, sticky="ew")
		details.grid_columnconfigure(0, weight=1)
		self.detail_rows: dict[str, ctk.CTkLabel] = {}
		for index, key in enumerate(DETAIL_KEYS):
			ctk.CTkLabel(
				details,
				text=key.upper(),
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=MUTED_GREEN,
				anchor="w",
			).grid(
				row=index * 2,
				column=0,
				padx=12,
				pady=(8 if index == 0 else 2, 0),
				sticky="ew",
			)
			value = ctk.CTkLabel(
				details,
				text="--",
				font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
				text_color=INK,
				anchor="w",
				wraplength=290,
				justify="left",
			)
			value.grid(row=index * 2 + 1, column=0, padx=12, pady=(0, 6), sticky="ew")
			self.detail_rows[key] = value

		ctk.CTkLabel(
			panel,
			text="QUEUE AT YOUR COUNTER",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			text_color=MUTED_GREEN,
			anchor="w",
		).grid(row=5, column=0, padx=16, pady=(12, 2), sticky="ew")
		self.queue_view = ctk.CTkTextbox(
			panel,
			height=150,
			activate_scrollbars=True,
			fg_color=SURFACE_ALT,
			border_color=PALE_BORDER,
			border_width=1,
			text_color=INK,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.queue_view.grid(row=6, column=0, padx=12, pady=(0, 8), sticky="ew")
		self.queue_view.configure(state="disabled")

		faq_frame = ctk.CTkFrame(panel, fg_color="transparent")
		faq_frame.grid(row=7, column=0, padx=16, pady=(0, 14), sticky="ew")
		faq_frame.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			faq_frame,
			text="HELPFUL QUESTIONS",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			text_color=MUTED_GREEN,
			anchor="w",
		).grid(row=0, column=0, pady=(0, 4), sticky="ew")
		self.faq_view = ctk.CTkTextbox(
			faq_frame,
			height=110,
			activate_scrollbars=True,
			fg_color=SURFACE_ALT,
			border_color=PALE_BORDER,
			border_width=1,
			text_color=INK,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			wrap="word",
		)
		self.faq_view.grid(row=1, column=0, sticky="ew")
		self.faq_view.configure(state="disabled")

	# ------------------------------------------------------------------
	# Actions
	# ------------------------------------------------------------------
	def _lookup_ticket(self) -> None:
		ticket_number = self.ticket_number.get().strip()
		if not ticket_number:
			self.lookup_feedback.set("Enter the ticket number printed on your receipt.")
			return
		try:
			ticket = get_recipient_ticket(ticket_number)
		except psycopg2.Error as error:
			self.lookup_feedback.set(f"Queue service unavailable: {error}")
			return
		except ValueError as error:
			self.lookup_feedback.set(str(error))
			return
		if ticket is None:
			self.ticket = None
			self.lookup_feedback.set(
				f'No ticket found for "{ticket_number}". Check the number and try again.'
			)
			self._render_ticket(None)
			return
		self.ticket = ticket
		self.counter_view = None
		self.lookup_feedback.set("Showing your live queue status.")
		self._render_ticket(ticket)
		self._load_faqs(ticket)

	def _clear_ticket(self) -> None:
		self.ticket = None
		self.counter_view = None
		self.ticket_number.set("")
		self.lookup_feedback.set("Enter your ticket number to track your place in line.")
		self._render_ticket(None)
		self._set_text(self.faq_view, "")

	def _lookup_counter(self, _value=None) -> None:
		"""Show the live queue for the counter chosen in the dropdown."""
		label = self.selected_counter.get()
		entry = None
		for candidate in self.board_data:
			if candidate["counter_label"] == label:
				entry = candidate
				break
		if entry is None:
			self.lookup_feedback.set("Choose a counter to view its live queue.")
			return
		self.ticket = None
		self.counter_view = entry
		self.lookup_feedback.set(
			f"Showing the live queue for {entry['counter_label']}."
		)
		self._render_counter_view(entry)

	def _render_counter_view(self, entry: dict) -> None:
		self.ticket_heading.configure(text=entry["counter_label"])
		self.ticket_status.configure(
			text="NOW SERVING" if entry["now_serving"] else "COUNTER IS CLEAR"
		)
		self.detail_rows["Recipient"].configure(text="Counter view")
		self.detail_rows["Service"].configure(
			text=", ".join(entry["concern_names"][:3]) or "Not specified"
		)
		self.detail_rows["Counter"].configure(text=entry["counter_label"])
		self.detail_rows["Your Position"].configure(
			text=f"{entry['waiting_count']} waiting"
		)
		average = entry["average_service_seconds"]
		if entry["waiting_count"]:
			estimate = average * max(entry["waiting_count"] - 1, 0) if average else 0
			self.detail_rows["Estimated Wait"].configure(
				text=format_duration(estimate) if estimate else "--"
			)
		else:
			self.detail_rows["Estimated Wait"].configure(text="No wait")

		waiting = entry["waiting"]
		if not waiting:
			self._set_text(self.queue_view, "No one is waiting at this counter.")
		else:
			self._set_text(
				self.queue_view,
				"\n".join(
					f"{index}.  {ticket_number}"
					for index, ticket_number in enumerate(waiting, 1)
				),
			)
		self._set_text(self.faq_view, "")

	def _load_faqs(self, ticket: dict) -> None:
		try:
			faqs = get_recipient_faqs_for_ticket(ticket)
		except (psycopg2.Error, ValueError):
			faqs = []
		if not faqs:
			self._set_text(self.faq_view, "No questions are published for this service yet.")
			return
		self._set_text(
			self.faq_view,
			"\n\n".join(f"{question}\n{answer}" for question, answer in faqs),
		)

	def _on_close(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
			self._refresh_job = None
		self.destroy()

	# ------------------------------------------------------------------
	# Rendering helpers
	# ------------------------------------------------------------------
	@staticmethod
	def _set_text(widget: ctk.CTkTextbox, text: str) -> None:
		widget.configure(state="normal")
		widget.delete("1.0", "end")
		widget.insert("1.0", text)
		widget.configure(state="disabled")

	def _counter_entry(self, counter_number: int) -> dict | None:
		for entry in self.board_data:
			if entry["counter_number"] == counter_number:
				return entry
		return None

	def _render_ticket(self, ticket: dict | None) -> None:
		if ticket is None:
			self.ticket_heading.configure(text="--")
			self.ticket_status.configure(text="")
			for value in self.detail_rows.values():
				value.configure(text="--")
			self._set_text(
				self.queue_view,
				"Look up a ticket to see the queue for your counter.",
			)
			return

		self.ticket_heading.configure(text=ticket["ticket_number"])
		self.ticket_status.configure(
			text=STATUS_LABELS.get(ticket["status"], ticket["status"].upper())
		)
		self.detail_rows["Recipient"].configure(
			text=ticket["recipient_name"] or "Not recorded"
		)
		self.detail_rows["Service"].configure(
			text=ticket["concern_name"] or "Not specified"
		)
		self.detail_rows["Counter"].configure(
			text=format_counter_label(ticket["counter_number"], ticket["counter_name"])
		)

		position = ticket["position"]
		if ticket["status"] == "waiting" and position:
			self.detail_rows["Your Position"].configure(text=f"#{position} in line")
		elif ticket["status"] == "serving":
			self.detail_rows["Your Position"].configure(text="Being served now")
		elif ticket["status"] == "completed":
			self.detail_rows["Your Position"].configure(text="Already served")
		else:
			self.detail_rows["Your Position"].configure(text="Not in queue")

		average = self._average_service_seconds(ticket["counter_number"])
		if ticket["status"] == "waiting" and position and average:
			estimate = average * max(position - 1, 0)
			self.detail_rows["Estimated Wait"].configure(text=format_duration(estimate))
		elif ticket["status"] == "serving":
			self.detail_rows["Estimated Wait"].configure(text="Now")
		elif ticket["status"] == "completed":
			self.detail_rows["Estimated Wait"].configure(text="Done")
		else:
			self.detail_rows["Estimated Wait"].configure(text="--")

		self._render_ticket_queue(ticket)

	def _render_ticket_queue(self, ticket: dict) -> None:
		entry = self._counter_entry(ticket["counter_number"])
		if entry is None:
			self._set_text(
				self.queue_view,
				"This counter is no longer active.",
			)
			return
		waiting = entry["waiting"]
		if not waiting:
			self._set_text(self.queue_view, "No one is waiting ahead of you.")
			return
		lines = []
		for index, ticket_number in enumerate(waiting, 1):
			marker = "  <-- you" if ticket_number == ticket["ticket_number"] else ""
			lines.append(f"{index}.  {ticket_number}{marker}")
		self._set_text(self.queue_view, "\n".join(lines))

	def _average_service_seconds(self, counter_number: int) -> float:
		entry = self._counter_entry(counter_number)
		if entry is None:
			return 0.0
		return entry["average_service_seconds"]

	# ------------------------------------------------------------------
	# Live counter board
	# ------------------------------------------------------------------
	def _render_board(self, board_data: list[dict]) -> None:
		for child in self.counter_grid.winfo_children():
			child.destroy()
		self._counter_panels = {}
		if not board_data:
			ctk.CTkLabel(
				self.counter_grid,
				text="No counters are active right now.",
				font=ctk.CTkFont(family=FONT_FAMILY, size=14),
				text_color=MUTED_TEXT,
			).grid(row=0, column=0, padx=12, pady=16, sticky="w")
			return
		for index, entry in enumerate(board_data):
			panel = ctk.CTkFrame(
				self.counter_grid,
				fg_color=SURFACE,
				corner_radius=8,
				border_width=1,
				border_color=BORDER,
			)
			panel.grid(row=index, column=0, padx=0, pady=(0, 10), sticky="ew")
			panel.grid_columnconfigure(0, weight=1)

			header = ctk.CTkFrame(panel, fg_color="transparent")
			header.grid(row=0, column=0, padx=14, pady=(10, 4), sticky="ew")
			header.grid_columnconfigure(1, weight=1)
			ctk.CTkLabel(
				header,
				text=format_counter_label(
					entry["counter_number"], entry["counter_name"]
				),
				font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
				text_color=INK,
				anchor="w",
			).grid(row=0, column=0, sticky="w")
			count_label = ctk.CTkLabel(
				header,
				text=f"{entry['waiting_count']} WAITING",
				fg_color=SOFT_GREEN,
				corner_radius=5,
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=GREEN,
				padx=9,
				pady=4,
			)
			count_label.grid(row=0, column=1, sticky="e")

			now_serving = ctk.CTkFrame(
				panel,
				fg_color=SURFACE_ALT,
				corner_radius=6,
				border_width=1,
				border_color=PALE_BORDER,
			)
			now_serving.grid(row=1, column=0, padx=10, pady=(2, 4), sticky="ew")
			now_serving.grid_columnconfigure(0, weight=1)
			ctk.CTkLabel(
				now_serving,
				text="NOW SERVING",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=MUTED_GREEN,
				anchor="w",
			).grid(row=0, column=0, padx=10, pady=(6, 0), sticky="ew")
			serving_value = ctk.CTkLabel(
				now_serving,
				text=entry["now_serving"] or "--",
				font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
				text_color=GREEN,
				anchor="w",
			)
			serving_value.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="ew")

			up_next = entry["waiting"][0] if entry["waiting"] else "--"
			up_next_label = ctk.CTkLabel(
				panel,
				text="UP NEXT",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color=MUTED_GREEN,
				anchor="w",
			)
			up_next_label.grid(row=2, column=0, padx=14, pady=(4, 0), sticky="ew")
			up_next_value = ctk.CTkLabel(
				panel,
				text=up_next,
				font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
				text_color=INK,
				anchor="w",
			)
			up_next_value.grid(row=3, column=0, padx=14, pady=(0, 2), sticky="ew")

			meta = ctk.CTkLabel(
				panel,
				text=self._board_meta(entry),
				font=ctk.CTkFont(family=FONT_FAMILY, size=10),
				text_color=MUTED_TEXT,
				anchor="w",
				justify="left",
				wraplength=520,
			)
			meta.grid(row=4, column=0, padx=14, pady=(0, 10), sticky="ew")

			self._counter_panels[entry["counter_number"]] = {
				"serving": serving_value,
				"up_next": up_next_value,
				"count": count_label,
				"meta": meta,
			}

	def _update_board(self) -> None:
		for entry in self.board_data:
			panel = self._counter_panels.get(entry["counter_number"])
			if panel is None:
				continue
			panel["serving"].configure(text=entry["now_serving"] or "--")
			panel["up_next"].configure(
				text=entry["waiting"][0] if entry["waiting"] else "--"
			)
			panel["count"].configure(text=f"{entry['waiting_count']} WAITING")
			panel["meta"].configure(text=self._board_meta(entry))

	@staticmethod
	def _board_meta(entry: dict) -> str:
		details = []
		if entry["serving_called_at"] is not None:
			details.append(f"Called at {format_clock(entry['serving_called_at'])}")
		if entry["average_service_seconds"]:
			details.append(
				f"Average service {format_duration(entry['average_service_seconds'])}"
			)
		if entry["concern_names"]:
			details.append("Services: " + ", ".join(entry["concern_names"][:4]))
		return "\n".join(details) if details else "No service data yet."

	def _layout_counter_panels(self, _event=None) -> None:
		"""Counter panels stack in a single column, so no re-layout is needed."""
		return

	# ------------------------------------------------------------------
	# Live refresh
	# ------------------------------------------------------------------
	def _refresh(self) -> None:
		try:
			board_data = get_recipient_queue_board()
			for entry in board_data:
				entry["counter_label"] = format_counter_label(
					entry["counter_number"], entry["counter_name"]
				)
			self._sync_counter_choices(board_data)
			signature = self._board_signature(board_data)
			if signature != self._board_key:
				self._board_key = signature
				self.board_data = board_data
				self._render_board(board_data)
			else:
				self.board_data = board_data
				self._update_board()
			self.status.set(
				f"Updated {datetime.now().strftime('%I:%M:%S %p').lstrip('0')}"
			)
			if self.ticket is not None:
				self._refresh_ticket()
			elif self.counter_view is not None:
				self._refresh_counter_view()
		except psycopg2.Error as error:
			self.status.set(f"Queue service unavailable: {error}")
		self._schedule_refresh()

	def _refresh_counter_view(self) -> None:
		"""Keep the selected counter panel in sync with the live queue."""
		if self.counter_view is None:
			return
		counter_number = self.counter_view["counter_number"]
		entry = self._counter_entry(counter_number)
		if entry is None:
			self.counter_view = None
			self.lookup_feedback.set("That counter is no longer active.")
			self._render_ticket(None)
			return
		self.counter_view = entry
		self._render_counter_view(entry)

	@staticmethod
	def _board_signature(board_data: list[dict]) -> tuple:
		"""Identify the set of counters so panels are only rebuilt when it changes."""
		return tuple(
			(entry["counter_number"], entry["counter_label"])
			for entry in board_data
		)

	def _sync_counter_choices(self, board_data: list[dict]) -> None:
		labels = [entry["counter_label"] for entry in board_data]
		if not labels:
			labels = ["Select a counter"]
		try:
			current = self.counter_choice.get()
		except (tk.TclError, ValueError):
			current = ""
		if current not in labels:
			current = labels[0]
		self.counter_choice.configure(values=labels)
		self.selected_counter.set(current)

	def _refresh_ticket(self) -> None:
		if self.ticket is None:
			return
		try:
			ticket = get_recipient_ticket(self.ticket["ticket_number"])
		except (psycopg2.Error, ValueError):
			return
		if ticket is None:
			self.ticket = None
			self.lookup_feedback.set("This ticket is no longer available.")
			self._render_ticket(None)
			return
		self.ticket = ticket
		self._render_ticket(ticket)

	def _schedule_refresh(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
		self._refresh_job = self.after(REFRESH_INTERVAL_MS, self._refresh)


def open_simulation(master=None) -> RecipientSimulationWindow:
	return RecipientSimulationWindow(master)
