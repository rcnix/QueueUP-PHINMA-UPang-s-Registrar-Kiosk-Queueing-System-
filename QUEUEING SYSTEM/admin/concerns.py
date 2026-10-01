import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from admin.styles import FONT_FAMILY, GREEN, GREEN_HOVER, INK
from database.queries import add_concern, delete_concern, get_concern_stats, get_concerns


class ConcernManagementMixin:
	def _build_concerns_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(3, weight=1)
		form = ctk.CTkFrame(tab)
		form.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
		self.concern_name = ctk.CTkEntry(
			form,
			placeholder_text="Concern name",
			width=240,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.concern_name.grid(row=0, column=0, padx=8, pady=10)
		self.concern_prefix = ctk.CTkEntry(
			form,
			placeholder_text="Ticket prefix",
			width=140,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.concern_prefix.grid(row=0, column=1, padx=8, pady=10)
		self.concern_counter = ctk.StringVar(value="COUNTER 1")
		ctk.CTkOptionMenu(
			form,
			variable=self.concern_counter,
			values=[f"COUNTER {number}" for number in range(1, self.COUNTER_COUNT + 1)],
			width=130,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		).grid(row=0, column=2, padx=8, pady=10)
		ctk.CTkButton(
			form,
			text="Add Concern",
			command=self._add_concern,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=0, column=3, padx=8, pady=10)
		ctk.CTkLabel(
			tab,
			text=(
				"A concern is a service offered at the kiosk. It defines the ticket prefix and routes the request "
				"to its assigned counter. Choosing a concern does not create a ticket; submitting at the kiosk does.\n"
				"Delete a concern to remove it from new kiosk requests. If tickets already use it, its history is retained."
			),
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			justify="left",
			wraplength=850,
			anchor="w",
		).grid(row=1, column=0, padx=12, pady=(4, 8), sticky="ew")
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
		ctk.CTkOptionMenu(
			service_controls,
			variable=self.concern_counter_filter,
			values=["ALL COUNTERS"]
			+ [f"COUNTER {number}" for number in range(1, self.COUNTER_COUNT + 1)],
			command=lambda _value: self._refresh_concerns(),
			width=150,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		).grid(row=0, column=1, sticky="e")
		self.concern_list = ctk.CTkScrollableFrame(tab)
		self.concern_list.grid(row=3, column=0, padx=10, pady=8, sticky="nsew")

	def _add_concern(self) -> None:
		try:
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
			add_concern(
				name,
				self.concern_prefix.get(),
				int(self.concern_counter.get().replace("COUNTER ", "")),
			)
			self.concern_name.delete(0, "end")
			self.concern_prefix.delete(0, "end")
			self.status.set("Concern added.")
			self._refresh_concerns()
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Concern error", str(error), parent=self)

	def _refresh_concerns(self) -> None:
		try:
			stats = {
				(name, counter): count
				for name, counter, count in get_concern_stats()
			}
			for child in self.concern_list.winfo_children():
				child.destroy()
			row = 0
			selected_counter = self.concern_counter_filter.get()
			for concern_id, name, prefix, counter, active in get_concerns(active_only=True):
				if selected_counter != "ALL COUNTERS" and counter != int(selected_counter.replace("COUNTER ", "")):
					continue
				ctk.CTkLabel(
					self.concern_list,
					text=(
						f"{name}  ({prefix})  -  COUNTER {counter}  -  "
						f"{stats.get((name, counter), 0)} tickets"
						+ ("  -  REMOVED FROM KIOSK" if not active else "")
					),
					anchor="w",
					font=ctk.CTkFont(family=FONT_FAMILY, size=12),
					text_color=INK,
				).grid(row=row, column=0, padx=8, pady=5, sticky="ew")
				ctk.CTkButton(
					self.concern_list,
					text="Delete" if active else "Removed",
					width=90,
					font=ctk.CTkFont(family=FONT_FAMILY, size=11),
					fg_color="#A64C42" if active else "#DDEBDD",
					hover_color="#873C34" if active else "#DDEBDD",
					text_color="white" if active else INK,
					state="normal" if active else "disabled",
					command=lambda key=concern_id, label=name: self._delete_concern(key, label),
				).grid(row=row, column=1, padx=8, pady=5)
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
