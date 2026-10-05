import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from assets import format_counter_label
from admin.styles import FONT_FAMILY, GREEN, GREEN_HOVER, INK
from database.queries import add_concern, delete_concern, get_concern_stats, get_concerns, get_counters


class ConcernManagementMixin:
	def _build_concerns_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(3, weight=1)
		form = ctk.CTkFrame(
			tab,
			fg_color="#F7FBF6",
			border_width=1,
			border_color="#BCD5BE",
			corner_radius=8,
		)
		form.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
		form.grid_columnconfigure((0, 1), weight=1)
		ctk.CTkLabel(
			form,
			text="ADD A SERVICE CONCERN",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color=GREEN,
			anchor="w",
		).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="ew")
		ctk.CTkLabel(
			form,
			text="Concern Name",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=1, column=0, padx=16, pady=(4, 2), sticky="ew")
		self.concern_name = ctk.CTkEntry(
			form,
			placeholder_text="e.g. Transcript Request",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.concern_name.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
		self.concern_counter = ctk.StringVar(value="Create a counter first")
		ctk.CTkLabel(
			form,
			text="Assigned Counter",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=1, column=1, padx=16, pady=(4, 2), sticky="ew")
		self.concern_counter_numbers: dict[str, int] = {}
		self.concern_counter_names: dict[int, str] = {}
		self.concern_counter_menu = ctk.CTkOptionMenu(
			form,
			variable=self.concern_counter,
			values=["Create a counter first"],
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.concern_counter_menu.grid(row=2, column=1, padx=16, pady=(0, 10), sticky="ew")
		self.concern_add_button = ctk.CTkButton(
			form,
			text="Add Concern to Kiosk",
			command=self._add_concern,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		)
		self.concern_add_button.grid(
			row=3, column=0, columnspan=2, padx=16, pady=(0, 14), sticky="ew"
		)
		ctk.CTkLabel(
			tab,
			text=(
				"A concern is a service offered at the kiosk. It routes the request to its assigned counter; "
				"tickets use that counter's fixed prefix. Choosing a concern does not create a ticket; submitting at the kiosk does.\n"
				"Delete a concern to remove it from new kiosk requests. If tickets already use it, its history is retained."
			),
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			justify="left",
			wraplength=850,
			anchor="w",
		).grid(row=1, column=0, padx=16, pady=(0, 10), sticky="ew")
		service_controls = ctk.CTkFrame(tab, fg_color="transparent")
		service_controls.grid(row=2, column=0, padx=12, pady=(0, 3), sticky="ew")
		service_controls.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			service_controls,
			text="SERVICES AND TICKET VOLUME",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, sticky="w")
		self.concern_counter_filter = tk.StringVar(value="ALL COUNTERS")
		self.concern_counter_filter_menu = ctk.CTkOptionMenu(
			service_controls,
			variable=self.concern_counter_filter,
			values=["ALL COUNTERS"],
			command=lambda _value: self._refresh_concerns(),
			width=150,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.concern_counter_filter_menu.grid(row=0, column=1, sticky="e")
		self.concern_list = ctk.CTkScrollableFrame(tab)
		self.concern_list.grid(row=3, column=0, padx=10, pady=8, sticky="nsew")
		self.concern_list.grid_columnconfigure(0, weight=1)
		self._refresh_concern_counter_options()

	def _refresh_concern_counter_options(self) -> None:
		try:
			counters = get_counters()
		except psycopg2.Error as error:
			self.status.set(f"Could not load counters: {error}")
			counters = []
		self.concern_counter_numbers = {
			format_counter_label(number, counter_name): number
			for number, counter_name, _prefix, _username in counters
		}
		self.concern_counter_names = {
			number: counter_name
			for number, counter_name, _prefix, _username in counters
		}
		values = list(self.concern_counter_numbers) or ["Create a counter first"]
		self.concern_counter_menu.configure(values=values, state="normal" if self.concern_counter_numbers else "disabled")
		if self.concern_counter.get() not in self.concern_counter_numbers:
			self.concern_counter.set(values[0])
		self.concern_add_button.configure(state="normal" if self.concern_counter_numbers else "disabled")
		self.concern_counter_filter_numbers = {
			format_counter_label(number, counter_name): number
			for number, counter_name, _prefix, _username in counters
		}
		filter_values = ["ALL COUNTERS", *self.concern_counter_filter_numbers]
		self.concern_counter_filter_menu.configure(values=filter_values)
		if self.concern_counter_filter.get() not in filter_values:
			self.concern_counter_filter.set("ALL COUNTERS")

	def _add_concern(self) -> None:
		try:
			self._refresh_concern_counter_options()
			name = self.concern_name.get().strip()
			existing_names = {
				concern[1].casefold() for concern in get_concerns(active_only=True)
			}
			if name.casefold() in existing_names:
				base_name = name
				suffix = 1
				while f"{base_name} ({suffix})".casefold() in existing_names:
					suffix += 1
				duplicate_name = f"{base_name} ({suffix})"
				if not messagebox.askyesno(
					"Duplicate concern",
					f'A concern named "{name}" was already made for this. '
					f'Do you wish to continue as "{duplicate_name}"?',
					parent=self,
				):
					return
				name = duplicate_name
			counter_number = self.concern_counter_numbers.get(self.concern_counter.get())
			if counter_number is None:
				raise ValueError("Create a counter before adding concerns")
			add_concern(name, counter_number)
			self.concern_name.delete(0, "end")
			self.status.set("Concern added.")
			self._refresh_concerns()
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Concern error", str(error), parent=self)

	def _refresh_concerns(self) -> None:
		try:
			self._refresh_concern_counter_options()
			stats = {
				(name, counter): count
				for name, counter, count in get_concern_stats()
			}
			for child in self.concern_list.winfo_children():
				child.destroy()
			row = 0
			selected_counter = self.concern_counter_filter_numbers.get(
				self.concern_counter_filter.get()
			)
			for concern_id, name, prefix, counter, active in get_concerns(active_only=True):
				if selected_counter is not None and counter != selected_counter:
					continue
				card = ctk.CTkFrame(
					self.concern_list,
					fg_color="#F7FBF6",
					border_width=1,
					border_color="#D8E8D9",
					corner_radius=6,
				)
				card.grid(row=row, column=0, columnspan=2, padx=5, pady=4, sticky="ew")
				card.grid_columnconfigure(0, weight=1)
				ctk.CTkLabel(
					card,
					text=name,
					anchor="w",
					font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
					text_color=GREEN,
				).grid(row=0, column=0, padx=12, pady=(8, 2), sticky="ew")
				detail = (
					f"Fixed prefix: {prefix}    "
					f"{format_counter_label(counter, self.concern_counter_names.get(counter, ''))}"
					f"    {stats.get((name, counter), 0)} tickets"
					+ ("    Removed from kiosk" if not active else "")
				)
				ctk.CTkLabel(
					card,
					text=detail,
					anchor="w",
					font=ctk.CTkFont(family=FONT_FAMILY, size=11),
					text_color=INK,
				).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")
				ctk.CTkButton(
					card,
					text="Delete" if active else "Removed",
					width=90,
					font=ctk.CTkFont(family=FONT_FAMILY, size=11),
					fg_color="#A64C42" if active else "#DDEBDD",
					hover_color="#873C34" if active else "#DDEBDD",
					text_color="white" if active else INK,
					state="normal" if active else "disabled",
					command=lambda key=concern_id, label=name: self._delete_concern(key, label),
				).grid(row=0, column=1, rowspan=2, padx=10, pady=8)
				row += 1
		except psycopg2.Error as error:
			self.status.set(f"Could not load concerns: {error}")

	def _delete_concern(self, concern_id: int, name: str) -> None:
		if not messagebox.askyesno(
			"Delete concern",
			f"Remove {name} from new kiosk requests? Existing ticket history will be retained.",
			parent=self,
		):
			return
		try:
			deleted = delete_concern(concern_id)
			self.status.set(
				f"{name} deleted."
				if deleted
				else f"{name} removed from the kiosk; its ticket history is retained."
			)
			self._refresh_concerns()
		except psycopg2.Error as error:
			messagebox.showerror("Delete concern error", str(error), parent=self)
