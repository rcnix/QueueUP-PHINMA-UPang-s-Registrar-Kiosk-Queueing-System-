# CONCERNS MANAGEMENT - ADMIN UI
# Manages service concerns that can be offered at counters, including adding,
# editing, deleting, and browsing service concerns and their ticket statistics.

import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from assets import format_counter_label
from admin.styles import (
ADMIN_CANVAS,
BORDER,
FONT_FAMILY,
GREEN,
GREEN_HOVER,
INK,
MUTED_TEXT,
SOFT_BORDER,
SOFT_GREEN,
SOFT_GREEN_HOVER,
SURFACE,
)
from admin.validation import set_field_error
from database.queries import add_concern, delete_concern, get_concern_stats, get_concerns, get_counters


# class ConcernManagementMixin - Mixin that provides concern management forms,
# browsing, filtering, and deletion of service concerns in the admin dashboard.
class ConcernManagementMixin:
	def _build_concerns_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(2, weight=1)
		form = ctk.CTkFrame(
			tab,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
			corner_radius=8,
		)
		form.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
		form.grid_columnconfigure((0, 1), weight=1)
		ctk.CTkLabel(
			form,
			text="ADD A SERVICE CONCERN",
			font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
			text_color=GREEN,
			anchor="w",
		).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="ew")
		ctk.CTkLabel(
			form,
			text=(
				"Offer a kiosk service, route it to a counter, and retain its ticket history "
				"when it is removed."
			),
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=MUTED_TEXT,
			anchor="w",
			wraplength=900,
			justify="left",
		).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="ew")
		ctk.CTkLabel(
			form,
			text="Concern Name",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=2, column=0, padx=16, pady=(4, 2), sticky="ew")
		self.concern_name = ctk.CTkEntry(
			form,
			height=34,
			placeholder_text="e.g. Transcript Request",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.concern_name.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
		self.concern_name_error = ctk.CTkLabel(
			form,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.concern_name_error.grid(row=4, column=0, padx=16, sticky="ew")
		self.concern_counter = ctk.StringVar(value="Create a counter first")
		ctk.CTkLabel(
			form,
			text="Assigned Counter",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=2, column=1, padx=16, pady=(4, 2), sticky="ew")
		self.concern_counter_numbers: dict[str, int] = {}
		self.concern_counter_names: dict[int, str] = {}
		self.concern_counter_menu = ctk.CTkOptionMenu(
			form,
			variable=self.concern_counter,
			values=["Create a counter first"],
			height=34,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.concern_counter_menu.grid(row=3, column=1, padx=16, pady=(0, 10), sticky="ew")
		self.concern_counter_error = ctk.CTkLabel(
			form,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.concern_counter_error.grid(row=4, column=1, padx=16, sticky="ew")
		self.concern_add_button = ctk.CTkButton(
			form,
			text="Add Concern to Kiosk",
			command=self._add_concern,
			height=36,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		)
		self.concern_add_button.grid(
			row=5, column=0, columnspan=2, padx=16, pady=(0, 14), sticky="ew"
		)
		service_controls = ctk.CTkFrame(tab, fg_color="transparent")
		service_controls.grid(row=1, column=0, padx=12, pady=(0, 5), sticky="ew")
		service_controls.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			service_controls,
			text="SERVICES AND TICKET VOLUME",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, padx=12, pady=8, sticky="w")
		self.concern_counter_filter = tk.StringVar(value="ALL COUNTERS")
		self.concern_counter_filter_menu = ctk.CTkOptionMenu(
			service_controls,
			variable=self.concern_counter_filter,
			values=["ALL COUNTERS"],
			command=lambda _value: self._refresh_concerns(),
			width=150,
			height=34,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.concern_counter_filter_menu.grid(row=0, column=1, padx=10, pady=5, sticky="e")
		self.concern_list = ctk.CTkScrollableFrame(
			tab,
			height=120,
			fg_color=ADMIN_CANVAS,
			border_width=1,
			border_color=SOFT_BORDER,
			corner_radius=8,
		)
		self.concern_list.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
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
		if not self._validate_concern_form():
			return
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

	def _validate_concern_form(self, show_required: bool = True) -> bool:
		name_message = (
			"Concern name is required."
			if show_required and not self.concern_name.get().strip()
			else ""
		)
		set_field_error(self.concern_name, self.concern_name_error, name_message)
		counter_number = self.concern_counter_numbers.get(self.concern_counter.get())
		counter_message = (
			"Choose an active counter."
			if show_required and counter_number is None
			else ""
		)
		self.concern_counter_error.configure(
			text=counter_message,
			text_color="#A64C42" if counter_message else MUTED_TEXT,
		)
		return not (name_message or counter_message)

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
					fg_color=SURFACE,
					border_width=1,
					border_color=SOFT_BORDER,
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
					fg_color="#A64C42" if active else SOFT_GREEN,
					hover_color="#873C34" if active else SOFT_GREEN,
					text_color="white" if active else INK,
					state="normal" if active else "disabled",
					command=lambda key=concern_id, label=name: self._delete_concern(key, label),
				).grid(row=0, column=1, rowspan=2, padx=10, pady=8)
				row += 1
			if row == 0:
				empty_message = (
					"No service concerns are assigned to this counter."
					if selected_counter is not None
					else "No service concerns yet. Add one above to offer services at the kiosk."
				)
				empty_state = ctk.CTkFrame(
					self.concern_list,
					fg_color=SURFACE,
					border_width=1,
					border_color=SOFT_BORDER,
					corner_radius=6,
				)
				empty_state.grid(row=0, column=0, padx=5, pady=8, sticky="ew")
				ctk.CTkLabel(
					empty_state,
					text=empty_message,
					font=ctk.CTkFont(family=FONT_FAMILY, size=12),
					text_color=INK,
					anchor="w",
				).pack(fill="x", padx=14, pady=14)
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
