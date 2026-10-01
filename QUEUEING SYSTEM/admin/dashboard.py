import calendar as month_calendar
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import ttk
from datetime import date, timedelta

import customtkinter as ctk
import psycopg2
from tkcalendar import DateEntry

from admin.calendar import AdminCalendarMixin
from admin.concerns import ConcernManagementMixin
from admin.styles import FONT_FAMILY, GREEN, GREEN_HOVER, INK
from database.queries import (
	get_concerns,
	get_faqs,
	get_latest_tickets,
	get_queue_snapshot,
	get_transactions,
	delete_faq,
	save_faq,
)


class AdminDashboard(ConcernManagementMixin, AdminCalendarMixin, ctk.CTkFrame):
	COUNTER_COUNT = 6
	TABLE_WEIGHTS = (1.0, 0.65, 0.8, 1.8, 1.25, 1.25, 1.25)

	def __init__(self, root):
		super().__init__(root, corner_radius=0)
		self.status = tk.StringVar(value="Administrative view connected.")
		self._refresh_job = None
		self._waiting_by_counter: dict[int, list[str]] = {}
		self._queue_hover_windows = {}
		self._queue_hover_jobs = {}
		self._initialize_calendar()
		self._transaction_filter_window = None
		self.faq_editor_id: int | None = None
		self.pack(fill="both", expand=True)
		self._build_ui()
		self._refresh_live_queues()
		self._refresh_transactions()
		self._refresh_concerns()
		self._load_calendar()

	def _build_ui(self) -> None:
		header = ctk.CTkFrame(self, fg_color="transparent")
		header.pack(fill="x", padx=22, pady=(14, 4))
		header.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			header,
			text="QueueUP Admin",
			font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, sticky="w")
		self.tabs = ctk.CTkTabview(self)
		self.tabs.pack(fill="both", expand=True, padx=18, pady=10)
		self.tabs.add("Live Queues")
		self.tabs.add("Transactions")
		self.tabs.add("Concerns")
		self.tabs.add("FAQ Editor")
		self.tabs.add("Calendar")
		self._build_live_tab(self.tabs.tab("Live Queues"))
		self._build_transactions_tab(self.tabs.tab("Transactions"))
		self._build_concerns_tab(self.tabs.tab("Concerns"))
		self._build_faq_editor_tab(self.tabs.tab("FAQ Editor"))
		self._build_calendar_tab(self.tabs.tab("Calendar"))
		ctk.CTkLabel(self, textvariable=self.status, anchor="center").pack(
			fill="x", padx=22, pady=(0, 10)
		)

	def _build_live_tab(self, tab) -> None:
		for row in range(2):
			tab.grid_rowconfigure(row, weight=1)
		for column in range(3):
			tab.grid_columnconfigure(column, weight=1)
		self.latest_labels = []
		self.serving_labels = []
		self.count_labels = []
		self.queue_views = []
		self.empty_queue_labels = []
		for index in range(self.COUNTER_COUNT):
			panel = ctk.CTkFrame(
				tab,
				fg_color="#F7FBF6",
				border_width=1,
				border_color="#BCD5BE",
				corner_radius=8,
			)
			panel.grid(
				row=index // 3,
				column=index % 3,
				padx=8,
				pady=8,
				sticky="nsew",
			)
			panel.grid_columnconfigure(0, weight=1)
			panel.grid_rowconfigure(6, weight=1)
			ctk.CTkLabel(
				panel,
				text=f"COUNTER {index + 1}",
				font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
				text_color=GREEN,
			).grid(row=0, column=0, padx=12, pady=(10, 5))
			ctk.CTkLabel(
				panel,
				text="LATEST TICKET",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color="#52765A",
			).grid(row=1, column=0, padx=10, pady=(1, 0))
			latest = ctk.CTkLabel(
				panel,
				text="--",
				font=ctk.CTkFont(family=FONT_FAMILY, size=19, weight="bold"),
				text_color=INK,
			)
			latest.grid(row=2, column=0, padx=10, pady=(0, 4))
			self.latest_labels.append(latest)
			ctk.CTkLabel(
				panel,
				text="NOW SERVING",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
				text_color="#52765A",
			).grid(row=3, column=0, padx=10, pady=(1, 0))
			serving = ctk.CTkLabel(
				panel,
				text="--",
				font=ctk.CTkFont(family=FONT_FAMILY, size=19, weight="bold"),
				text_color=INK,
			)
			serving.grid(row=4, column=0, padx=10, pady=(0, 4))
			self.serving_labels.append(serving)
			count = ctk.CTkLabel(
				panel,
				text="Waiting: 0",
				font=ctk.CTkFont(family=FONT_FAMILY, size=11),
				text_color=INK,
			)
			count.grid(row=5, column=0, padx=10, pady=3)
			self.count_labels.append(count)
			queue_view = ctk.CTkTextbox(
				panel,
				height=84,
				activate_scrollbars=False,
				fg_color="#EDF6ED",
				border_color="#D1E4D2",
				border_width=1,
				text_color=INK,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			)
			queue_view.grid(row=6, column=0, padx=10, pady=(4, 10), sticky="nsew")
			queue_view.configure(state="disabled")
			for hover_target in (queue_view, queue_view._textbox):
				hover_target.bind(
					"<Enter>", lambda event, i=index: self._show_queue_hover(event, i)
				)
				hover_target.bind(
					"<Leave>", lambda _event, i=index: self._schedule_queue_hover_close(i)
				)
			self.queue_views.append(queue_view)
			empty_label = ctk.CTkLabel(
				panel,
				text="No more waiting tickets",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color="#52765A",
				fg_color="#EDF6ED",
				anchor="center",
			)
			empty_label.grid(row=6, column=0, padx=10, pady=(4, 10), sticky="nsew")
			empty_label.grid_remove()
			self.empty_queue_labels.append(empty_label)

	def _refresh_live_queues(self) -> None:
		try:
			snapshot = get_queue_snapshot()
			latest_tickets = get_latest_tickets()
			for counter_number, view in enumerate(self.queue_views, 1):
				serving, waiting = snapshot[counter_number]
				self.latest_labels[counter_number - 1].configure(
					text=latest_tickets[counter_number] or "--"
				)
				self.serving_labels[counter_number - 1].configure(text=serving or "--")
				self.count_labels[counter_number - 1].configure(
					text=f"Waiting: {len(waiting)}"
				)
				self._waiting_by_counter[counter_number] = list(waiting)
				if waiting:
					self.empty_queue_labels[counter_number - 1].grid_remove()
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
					self.empty_queue_labels[counter_number - 1].grid()
			self.status.set("Live queue status updated.")
		except psycopg2.Error as error:
			self.status.set(f"Could not refresh live queues: {error}")
		if self.winfo_exists():
			if self._refresh_job is not None:
				try:
					self.after_cancel(self._refresh_job)
				except tk.TclError:
					pass
			self._refresh_job = self.after(2000, self._refresh_live_queues)

	def _show_queue_hover(self, event, index: int) -> None:
		counter_number = index + 1
		waiting = self._waiting_by_counter.get(counter_number, [])
		if not waiting or not self._queue_overflows(self.queue_views[index]):
			return
		if index in self._queue_hover_windows:
			return
		popup = ctk.CTkToplevel(self)
		popup.wm_overrideredirect(True)
		popup.geometry(f"+{event.x_root + 14}+{event.y_root + 14}")
		popup.attributes("-topmost", True)
		popup.configure(fg_color="#F7FBF6")
		self._queue_hover_windows[index] = popup
		popup.bind("<Enter>", lambda _event, i=index: self._cancel_queue_hover_close(i))
		popup.bind("<Leave>", lambda _event, i=index: self._schedule_queue_hover_close(i))
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
			fg_color="#E8F3E8",
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
		controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
		self.transaction_counter = tk.StringVar(value="ALL COUNTERS")
		ctk.CTkOptionMenu(
			controls,
			variable=self.transaction_counter,
			values=["ALL COUNTERS"]
			+ [f"COUNTER {number}" for number in range(1, self.COUNTER_COUNT + 1)],
			command=lambda _value: self._refresh_transactions(),
			width=130,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		).pack(side="left", padx=(0, 8))
		self.all_transactions = tk.BooleanVar(value=False)
		ctk.CTkSwitch(
			controls,
			text="All history",
			variable=self.all_transactions,
			command=self._refresh_transactions,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		).pack(side="left", padx=8)
		ctk.CTkLabel(
			controls,
			text="History date",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
		).pack(side="left", padx=(8, 4))
		self.transaction_history_date = DateEntry(
			controls,
			date_pattern="yyyy-mm-dd",
			font=(FONT_FAMILY, 10),
			width=11,
		)
		self.transaction_history_date.pack(side="left", padx=(0, 8))
		self.transaction_history_date.bind(
			"<<DateEntrySelected>>", self._on_transaction_history_date_selected
		)
		self.transaction_history_date.bind(
			"<FocusOut>", self._on_transaction_history_date_selected, add="+"
		)
		ctk.CTkButton(
			controls,
			text="Refresh Transactions",
			command=self._refresh_transactions,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).pack(side="left")
		ctk.CTkButton(
			controls,
			text="Filter",
			command=self._open_transaction_filter,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color="#DDEBDD",
			hover_color="#C6DEC7",
			text_color=INK,
		).pack(side="left", padx=6)
		self.transaction_range_label = ctk.CTkLabel(
			controls,
			text="All issued tickets" if self.all_transactions.get() else "",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
		)
		self.transaction_range_label.pack(side="right", padx=12)
		self.transaction_search = tk.StringVar(value="")
		ctk.CTkEntry(
			controls,
			textvariable=self.transaction_search,
			placeholder_text="Recipient name",
			width=190,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		).pack(side="right", padx=(8, 4))
		ctk.CTkButton(
			controls,
			text="Search",
			width=74,
			command=self._refresh_transactions,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).pack(side="right", padx=4)
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
				fg_color="#DDEBDD",
				anchor="center",
				justify="center",
			).grid(row=0, column=column, padx=1, pady=(0, 2), sticky="ew")

	def _open_transaction_filter(self) -> None:
		if self._transaction_filter_window is not None:
			if self._transaction_filter_window.winfo_exists():
				self._close_transaction_filter()
				return
		window = ctk.CTkToplevel(self)
		self._transaction_filter_window = window
		window.title("Filter transactions")
		window.geometry("500x560")
		window.minsize(460, 520)
		window.transient(self.winfo_toplevel())
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
			width=14,
		)
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
			("Counter", self.transaction_counter, ["ALL COUNTERS"] + [
				f"COUNTER {number}" for number in range(1, self.COUNTER_COUNT + 1)
			]),
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
			ctk.CTkOptionMenu(
				window,
				variable=variable,
				values=values,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				fg_color=GREEN,
				button_color=GREEN_HOVER,
				button_hover_color=INK,
			).grid(row=row, column=1, padx=(0, 20), pady=7, sticky="ew")
		window.grid_rowconfigure(len(fields) + len(options) + 2, weight=1)
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
			fg_color="#DDEBDD",
			hover_color="#C6DEC7",
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
				counter_number=(
					None
					if selected_counter == "ALL COUNTERS"
					else int(selected_counter.replace("COUNTER ", ""))
				),
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
					fg_color="#DDEBDD",
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
						fg_color="#F7FBF6" if row_index % 2 == 0 else "#EDF6ED",
						anchor="center",
						justify="center",
						wraplength=190 if column == 3 else 125,
					)
					cell.grid(row=row_index + 1, column=column, padx=1, pady=1, sticky="nsew")
		except psycopg2.Error as error:
			self.status.set(f"Could not load transactions: {error}")

	def _build_faq_editor_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		controls = ctk.CTkFrame(tab, fg_color="transparent")
		controls.grid(row=0, column=0, padx=12, pady=10, sticky="ew")
		self.faq_scope = tk.StringVar(value="Counter")
		self.faq_target = tk.StringVar(value="COUNTER 1")
		self.faq_target_ids: dict[str, int] = {}
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

		ctk.CTkLabel(
			tab,
			text="Question",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
		).grid(row=1, column=0, padx=14, pady=(4, 2), sticky="w")
		self.faq_question = tk.StringVar(value="")
		ctk.CTkEntry(
			tab,
			textvariable=self.faq_question,
			placeholder_text="Enter a frequently asked question",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		).grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
		ctk.CTkLabel(
			tab,
			text="Answer",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
		).grid(row=3, column=0, padx=14, pady=(0, 2), sticky="w")
		self.faq_answer = ctk.CTkTextbox(
			tab,
			height=86,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.faq_answer.grid(row=4, column=0, padx=12, pady=(0, 8), sticky="ew")
		buttons = ctk.CTkFrame(tab, fg_color="transparent")
		buttons.grid(row=5, column=0, padx=12, pady=(0, 6), sticky="ew")
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
			fg_color="#DDEBDD",
			hover_color="#C6DEC7",
			text_color=INK,
		)
		self.faq_cancel_button.pack(side="left", padx=8)
		self.faq_cancel_button.pack_forget()
		self.faq_editor_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
		self.faq_editor_list.grid(row=6, column=0, padx=10, pady=(2, 10), sticky="nsew")
		tab.grid_rowconfigure(6, weight=1)
		self._refresh_faq_editor_targets()

	def _on_faq_scope_changed(self) -> None:
		self._clear_faq_editor_form()
		self._refresh_faq_editor_targets()

	def _on_faq_target_changed(self) -> None:
		self._clear_faq_editor_form()
		self._refresh_faq_editor_list()

	def _refresh_faq_editor_targets(self) -> None:
		if self.faq_scope.get() == "Counter":
			self.faq_target_ids = {
				f"COUNTER {number}": number
				for number in range(1, self.COUNTER_COUNT + 1)
			}
		else:
			try:
				self.faq_target_ids = {
					f"{name} ({prefix})": concern_id
					for concern_id, name, prefix, _counter, _active in get_concerns(active_only=True)
				}
			except psycopg2.Error as error:
				self.status.set(f"Could not load FAQ concerns: {error}")
				self.faq_target_ids = {}
		values = list(self.faq_target_ids) or ["No active concerns"]
		self.faq_target_menu.configure(values=values)
		current = self.faq_target.get()
		self.faq_target.set(current if current in self.faq_target_ids else values[0])
		self.faq_target_menu.configure(
			state="normal" if self.faq_target_ids else "disabled"
		)
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
			row = ctk.CTkFrame(self.faq_editor_list, fg_color="#F7FBF6")
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
				text_color="#657267",
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
		self.faq_save_button.configure(text="Save changes")
		self.faq_cancel_button.pack(side="left", padx=8)

	def _clear_faq_editor_form(self) -> None:
		self.faq_editor_id = None
		self.faq_question.set("")
		self.faq_answer.delete("1.0", "end")
		if hasattr(self, "faq_save_button"):
			self.faq_save_button.configure(text="Add FAQ")
			self.faq_cancel_button.pack_forget()

	def _save_faq_editor_entry(self) -> None:
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
		self.calendar_month = ttk.Combobox(
			controls,
			values=list(month_calendar.month_name)[1:],
			state="readonly",
			width=11,
		)
		self.calendar_month.current(self._calendar_date.month - 1)
		self.calendar_month.bind(
			"<<ComboboxSelected>>", lambda _event: self._load_calendar()
		)
		self.calendar_month.pack(side="left", padx=(0, 6))
		self.calendar_year = ttk.Combobox(
			controls,
			values=[str(year) for year in range(1900, 2101)],
			state="readonly",
			width=6,
		)
		self.calendar_year.set(str(self._calendar_date.year))
		self.calendar_year.bind(
			"<<ComboboxSelected>>", lambda _event: self._load_calendar()
		)
		self.calendar_year.pack(side="left", padx=6)
		self.month_title = ctk.CTkLabel(
			controls,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
			text_color=INK,
		)
		self.month_title.pack(side="left", padx=14)
		self.calendar_counter = tk.StringVar(value="ALL COUNTERS")
		ctk.CTkOptionMenu(
			controls,
			variable=self.calendar_counter,
			values=["ALL COUNTERS"]
			+ [f"COUNTER {number}" for number in range(1, self.COUNTER_COUNT + 1)],
			command=lambda _value: self._load_calendar(),
			width=145,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		).pack(side="left", padx=6)
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
			fg_color="#F7FBF6",
			border_width=1,
			border_color="#BCD5BE",
			corner_radius=8,
		)
		self.calendar_grid.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
		self.day_panel = ctk.CTkFrame(
			tab,
			fg_color="#F7FBF6",
			border_width=1,
			border_color="#BCD5BE",
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
		month = self.calendar_month.current() + 1
		year = int(self.calendar_year.get())
		month_index = year * 12 + month - 1 + offset
		year, month_index = divmod(month_index, 12)
		self.calendar_month.current(month_index)
		self.calendar_year.set(str(year))
		self._load_calendar()

	@staticmethod
	def _set_text(widget, value: str) -> None:
		widget.configure(state="normal")
		widget.delete("1.0", "end")
		widget.insert("1.0", value)
		widget.configure(state="disabled")

	def destroy(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
		super().destroy()