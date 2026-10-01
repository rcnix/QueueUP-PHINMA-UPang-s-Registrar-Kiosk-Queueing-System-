from datetime import date
import calendar as month_calendar

import customtkinter as ctk
import psycopg2

from admin.styles import FONT_FAMILY, GREEN, INK
from database.queries import get_daily_transactions, get_monthly_ticket_counts


class AdminCalendarMixin:
	def _initialize_calendar(self) -> None:
		self._calendar_date = date.today().replace(day=1)
		self._selected_date = date.today()

	def _load_calendar(self) -> None:
		try:
			month = self.calendar_month.current() + 1
			year = int(self.calendar_year.get())
			self._calendar_date = date(year, month, 1)
			selected_counter = self.calendar_counter.get()
			counter_number = (
				None
				if selected_counter == "ALL COUNTERS"
				else int(selected_counter.replace("COUNTER ", ""))
			)
			counts = get_monthly_ticket_counts(year, month, counter_number)
		except (ValueError, psycopg2.Error) as error:
			self.status.set(f"Could not load calendar: {error}")
			return
		self.month_title.configure(text=self._calendar_date.strftime("%B %Y"))
		for child in self.calendar_grid.winfo_children():
			child.destroy()
		for column in range(7):
			self.calendar_grid.grid_columnconfigure(column, weight=1, uniform="calendar-day")
		for row in range(7):
			self.calendar_grid.grid_rowconfigure(row, weight=1, uniform="calendar-week")
		self.calendar_buttons = {}
		self.calendar_counts = {}
		for column, weekday in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
			ctk.CTkLabel(
				self.calendar_grid,
				text=weekday.upper(),
				font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
				text_color=GREEN,
			).grid(row=0, column=column, padx=3, pady=(6, 2), sticky="nsew")
		for row, week in enumerate(month_calendar.monthcalendar(year, month), 1):
			for column, day_number in enumerate(week):
				if day_number == 0:
					ctk.CTkFrame(self.calendar_grid, fg_color="transparent").grid(
						row=row, column=column, padx=3, pady=3, sticky="nsew"
					)
					continue
				day_date = date(year, month, day_number)
				count = counts.get(day_date, 0)
				self.calendar_counts[day_date] = count
				button = ctk.CTkButton(
					self.calendar_grid,
					text=f"{day_number:02d}\n{count} TICKETS",
					font=ctk.CTkFont(family=FONT_FAMILY, size=10),
					text_color=INK,
					fg_color="#E8F3E8" if count else "#F7FBF6",
					hover_color="#D6E9D7",
					border_width=1,
					border_color="#D1E4D2",
					corner_radius=5,
					command=lambda selected=day_date: self._show_day(selected),
				)
				button.grid(row=row, column=column, padx=3, pady=3, sticky="nsew")
				self.calendar_buttons[day_date] = button
		self._selected_date = (
			date.today()
			if date.today().year == year and date.today().month == month
			else self._calendar_date
		)
		self._show_day(self._selected_date)

	def _show_day(self, selected_date: date) -> None:
		self._selected_date = selected_date
		for day_date, button in self.calendar_buttons.items():
			count = self.calendar_counts.get(day_date, 0) > 0
			button.configure(
				fg_color=(
					"#A9D2AD"
					if day_date == selected_date
					else "#E8F3E8"
					if count
					else "#F7FBF6"
				),
				border_color=GREEN if day_date == selected_date else "#D1E4D2",
			)
		try:
			selected_counter = self.calendar_counter.get()
			counter_number = (
				None
				if selected_counter == "ALL COUNTERS"
				else int(selected_counter.replace("COUNTER ", ""))
			)
			rows = get_daily_transactions(selected_date, counter_number)
			self.day_transaction_title.configure(
				text=f"{selected_date:%b %d}  /  {len(rows)} TICKETS"
			)
			for child in self.day_transactions.winfo_children():
				child.destroy()
			if not rows:
				ctk.CTkLabel(
					self.day_transactions,
					text="No tickets issued on this date.",
					font=ctk.CTkFont(family=FONT_FAMILY, size=12),
					text_color=INK,
				).pack(anchor="w", padx=8, pady=14)
			for ticket, concern, counter, status, recipient, created, _called, _completed in rows:
				card = ctk.CTkFrame(
					self.day_transactions,
					fg_color="#F7FBF6",
					border_width=1,
					border_color="#D8E8D9",
					corner_radius=5,
				)
				card.pack(fill="x", padx=2, pady=3)
				ctk.CTkLabel(
					card,
					text=ticket,
					font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
					text_color=GREEN,
					anchor="w",
				).pack(fill="x", padx=10, pady=(7, 0))
				ctk.CTkLabel(
					card,
					text=f"{recipient or 'Recipient not recorded'}  /  {concern or 'Legacy ticket'}",
					font=ctk.CTkFont(family=FONT_FAMILY, size=11),
					text_color=INK,
					anchor="w",
					wraplength=420,
				).pack(fill="x", padx=10, pady=(0, 2))
				ctk.CTkLabel(
					card,
					text=f"COUNTER {counter}  /  {status.upper()}  /  {created:%H:%M}",
					font=ctk.CTkFont(family=FONT_FAMILY, size=10),
					text_color="#52765A",
					anchor="w",
				).pack(fill="x", padx=10, pady=(0, 7))
				for widget in (card, *card.winfo_children()):
					widget.bind(
						"<Enter>",
						lambda _event, item=card: item.configure(fg_color="#E8F3E8"),
					)
					widget.bind(
						"<Leave>",
						lambda _event, item=card: item.configure(fg_color="#F7FBF6"),
					)
		except psycopg2.Error as error:
			self.status.set(f"Could not load that date: {error}")