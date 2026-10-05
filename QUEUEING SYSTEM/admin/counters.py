import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from assets import format_counter_label, set_window_icon
from admin.styles import FONT_FAMILY, GREEN, GREEN_HOVER, INK
from database.queries import (
	authenticate_admin_password,
	create_counter_account,
	delete_counter_account,
	get_counter_password_map,
	get_counters,
)


class CounterCreationMixin:
	def _build_counter_creation_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(1, weight=1)
		form = ctk.CTkFrame(
			tab,
			fg_color="#F7FBF6",
			border_width=1,
			border_color="#BCD5BE",
			corner_radius=8,
		)
		form.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
		for column in range(2):
			form.grid_columnconfigure(column, weight=1)
		ctk.CTkLabel(
			form,
			text="CREATE A COUNTER ACCOUNT",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color=GREEN,
			anchor="w",
		).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="ew")
		fields = (
			("Counter Name", "counter_name_entry", "e.g. COUNTER 1", False),
			("Fixed Prefix", "counter_prefix_entry", "1-6 letters or numbers", False),
			("Counter User", "counter_username_entry", "Username for counter sign-in", False),
			("Password", "counter_password_entry", "At least 8 characters", True),
		)
		for index, (label, attribute, placeholder, masked) in enumerate(fields):
			row = 1 + (index // 2) * 2
			column = index % 2
			ctk.CTkLabel(
				form,
				text=label,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
				text_color=INK,
				anchor="w",
			).grid(row=row, column=column, padx=16, pady=(5, 2), sticky="ew")
			entry = ctk.CTkEntry(
				form,
				placeholder_text=placeholder,
				show="*" if masked else "",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			)
			entry.grid(row=row + 1, column=column, padx=16, pady=(0, 8), sticky="ew")
			setattr(self, attribute, entry)
		ctk.CTkLabel(
			form,
			text="Confirm Password",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=5, column=0, padx=16, pady=(5, 2), sticky="ew")
		self.counter_password_confirm_entry = ctk.CTkEntry(
			form,
			placeholder_text="Re-enter the counter password",
			show="*",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_password_confirm_entry.grid(
			row=6, column=0, padx=16, pady=(0, 8), sticky="ew"
		)
		ctk.CTkButton(
			form,
			text="Create Counter",
			command=self._create_counter_account,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=6, column=1, padx=16, pady=(0, 8), sticky="ew")
		ctk.CTkLabel(
			form,
			text="Each counter gets one fixed ticket prefix and a counter-only login.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="w",
		).grid(row=7, column=0, padx=16, pady=(0, 2), sticky="ew")
		ctk.CTkButton(
			form,
			text="Open Password Map",
			command=self._request_password_map_access,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color="#DDEBDD",
			hover_color="#C6DEC7",
			text_color=INK,
		).grid(row=7, column=1, padx=16, pady=(0, 12), sticky="ew")
		self.counter_account_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
		self.counter_account_list.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
		self._refresh_counter_accounts()

	def _create_counter_account(self) -> None:
		password = self.counter_password_entry.get()
		if len(password) < 8:
			messagebox.showwarning(
				"Password too short",
				"Counter passwords must contain at least 8 characters.",
				parent=self,
			)
			return
		if password != self.counter_password_confirm_entry.get():
			messagebox.showwarning(
				"Passwords do not match",
				"Enter the same password in both password fields.",
				parent=self,
			)
			return
		try:
			counter_number = create_counter_account(
				self.counter_name_entry.get(),
				self.counter_prefix_entry.get(),
				self.counter_username_entry.get(),
				password,
			)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Counter creation failed", str(error), parent=self)
			return
		for entry in (
			self.counter_name_entry,
			self.counter_prefix_entry,
			self.counter_username_entry,
			self.counter_password_entry,
			self.counter_password_confirm_entry,
		):
			entry.delete(0, "end")
		self.status.set(f"Counter {counter_number} created.")
		self._refresh_counter_accounts()
		self._on_counters_changed()

	def _request_password_map_access(self) -> None:
		prompt = ctk.CTkToplevel(self)
		prompt.title("Admin verification")
		prompt.geometry("390x220")
		prompt.resizable(False, False)
		prompt.transient(self.winfo_toplevel())
		prompt.grab_set()
		set_window_icon(prompt)
		prompt.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			prompt,
			text="ADMIN PASSWORD REQUIRED",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, padx=22, pady=(22, 6))
		ctk.CTkLabel(
			prompt,
			text="Verify your admin password to open saved counter credentials.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			wraplength=330,
		).grid(row=1, column=0, padx=22, pady=(0, 8))
		password_entry = ctk.CTkEntry(
			prompt,
			placeholder_text="Admin password",
			show="*",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		password_entry.grid(row=2, column=0, padx=22, pady=6, sticky="ew")

		def verify_access() -> None:
			try:
				is_admin = authenticate_admin_password(password_entry.get())
			except psycopg2.Error as error:
				messagebox.showerror(
					"Admin verification failed", str(error), parent=prompt
				)
				return
			if not is_admin:
				messagebox.showerror(
					"Access denied",
					"The admin password is incorrect.",
					parent=prompt,
				)
				password_entry.focus_set()
				return
			prompt.destroy()
			self._show_password_map()

		ctk.CTkButton(
			prompt,
			text="Verify and Open",
			command=verify_access,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=3, column=0, padx=22, pady=(8, 16), sticky="ew")
		password_entry.bind("<Return>", lambda _event: verify_access())
		password_entry.focus_set()

	def _show_password_map(self) -> None:
		try:
			credentials = get_counter_password_map()
		except psycopg2.Error as error:
			messagebox.showerror("Password map error", str(error), parent=self)
			return
		window = ctk.CTkToplevel(self)
		window.title("Counter Password Map")
		window.geometry("760x480")
		window.minsize(600, 360)
		window.transient(self.winfo_toplevel())
		set_window_icon(window)
		window.grid_columnconfigure(0, weight=1)
		window.grid_rowconfigure(2, weight=1)
		ctk.CTkLabel(
			window,
			text="COUNTER PASSWORD MAP",
			font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")
		ctk.CTkLabel(
			window,
			text="Existing passwords created before this map was added cannot be recovered.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
		).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
		table = ctk.CTkScrollableFrame(window, fg_color="transparent")
		table.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="nsew")
		for column, weight in enumerate((1, 1, 1.4)):
			table.grid_columnconfigure(column, weight=int(weight * 100))
		for column, title in enumerate(("COUNTER", "COUNTER USER", "PASSWORD")):
			ctk.CTkLabel(
				table,
				text=title,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
				text_color=GREEN,
				fg_color="#DDEBDD",
				anchor="w",
			).grid(row=0, column=column, padx=2, pady=(0, 4), sticky="ew")
		if not credentials:
			ctk.CTkLabel(
				table,
				text="No counter accounts have been created.",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color=INK,
			).grid(row=1, column=0, columnspan=3, padx=8, pady=16, sticky="w")
		for row, (number, name, username, password) in enumerate(credentials, 1):
			values = (
				format_counter_label(number, name),
				username,
				password if password is not None else "Not stored (legacy account)",
			)
			for column, value in enumerate(values):
				ctk.CTkLabel(
					table,
					text=value,
					font=ctk.CTkFont(family=FONT_FAMILY, size=12),
					text_color=INK,
					anchor="w",
					wraplength=260,
				).grid(row=row, column=column, padx=8, pady=7, sticky="ew")

	def _refresh_counter_accounts(self) -> None:
		for child in self.counter_account_list.winfo_children():
			child.destroy()
		try:
			counters = get_counters()
		except psycopg2.Error as error:
			self.status.set(f"Could not load counters: {error}")
			return
		if not counters:
			ctk.CTkLabel(
				self.counter_account_list,
				text="No counters have been created.",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color=INK,
			).grid(row=0, column=0, padx=8, pady=8, sticky="w")
			return
		for row, (number, name, prefix, username) in enumerate(counters):
			card = ctk.CTkFrame(
				self.counter_account_list,
				fg_color="#F7FBF6",
				border_width=1,
				border_color="#D8E8D9",
				corner_radius=6,
			)
			card.grid(row=row, column=0, padx=5, pady=4, sticky="ew")
			card.grid_columnconfigure(0, weight=1)
			card.grid_columnconfigure(1, weight=0)
			ctk.CTkLabel(
				card,
				text=format_counter_label(number, name),
				font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
				text_color=GREEN,
				anchor="w",
			).grid(row=0, column=0, padx=12, pady=(8, 2), sticky="ew")
			ctk.CTkLabel(
				card,
				text=f"Fixed prefix: {prefix}    Counter user: {username}",
				font=ctk.CTkFont(family=FONT_FAMILY, size=11),
				text_color=INK,
				anchor="w",
			).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")
			ctk.CTkButton(
				card,
				text="Delete User",
				width=110,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
				fg_color="#A64C42",
				hover_color="#873C34",
				command=lambda key=number, label=name, user=username: self._delete_counter_account(
					key, label, user
				),
			).grid(row=0, column=1, rowspan=2, padx=12, pady=8)

	def _delete_counter_account(
		self,
		counter_number: int,
		counter_name: str,
		username: str,
	) -> None:
		if not messagebox.askyesno(
			"Delete counter user?",
			f'Delete the counter user "{username}" and remove '
			f"{format_counter_label(counter_number, counter_name)} from the kiosk?\n\n"
			"Assigned concerns will be deactivated. Existing ticket history will be retained. "
			"This action cannot be undone.",
			icon="warning",
			parent=self,
		):
			return
		try:
			deleted = delete_counter_account(counter_number)
		except psycopg2.Error as error:
			messagebox.showerror("User deletion failed", str(error), parent=self)
			return
		if not deleted:
			messagebox.showerror(
				"User not found",
				"The counter user no longer exists. Refresh the counter list.",
				parent=self,
			)
			self._refresh_counter_accounts()
			self._on_counters_changed()
			return
		self.status.set(f"Counter user {username} deleted.")
		self._refresh_counter_accounts()
		self._on_counters_changed()
