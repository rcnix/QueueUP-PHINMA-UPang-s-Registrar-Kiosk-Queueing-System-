import re
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from assets import format_counter_label, set_window_icon
from admin.styles import (
	BORDER,
	FONT_FAMILY,
	GREEN,
	GREEN_HOVER,
	INK,
	SOFT_BORDER,
	SOFT_GREEN,
	SOFT_GREEN_HOVER,
	SURFACE,
)
from database.queries import (
	authenticate_admin_password,
	create_counter_account,
	delete_counter_account,
	get_counter_password_map,
	get_counters,
	update_counter_account,
)
from database.models import MAX_COUNTERS
from admin.validation import set_field_error


class CounterCreationMixin:
	def _build_counter_creation_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(1, weight=1)
		form = ctk.CTkFrame(
			tab,
			fg_color=SURFACE,
			border_width=1,
			border_color=BORDER,
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
			("Fixed Prefix", "counter_prefix_entry", "1-6 letters or numbers", False, 1, 1, "counter_prefix_error"),
			("Counter User", "counter_username_entry", "Username for counter sign-in", False, 4, 0, "counter_username_error"),
			("Password", "counter_password_entry", "At least 8 characters", True, 4, 1, "counter_password_error"),
		)
		for label, attribute, placeholder, masked, row, column, error_attribute in fields:
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
			feedback = ctk.CTkLabel(
				form,
				text="",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10),
				text_color="#A64C42",
				anchor="w",
			)
			feedback.grid(row=row + 2, column=column, padx=16, sticky="ew")
			setattr(self, error_attribute, feedback)
		ctk.CTkLabel(
			form,
			text="Counter Number (1-100)",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=1, column=0, padx=16, pady=(5, 2), sticky="ew")
		self.counter_number_entry = ctk.CTkEntry(
			form,
			placeholder_text=f"1 to {MAX_COUNTERS}",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_number_entry.grid(
			row=2, column=0, padx=16, pady=(0, 8), sticky="ew"
		)
		ctk.CTkLabel(
			form,
			text="Window Name",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=7, column=0, padx=16, pady=(5, 2), sticky="ew")
		self.counter_name_entry = ctk.CTkEntry(
			form,
			placeholder_text="Enter the name shown for this window",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_name_entry.grid(
			row=8, column=0, padx=16, pady=(0, 8), sticky="ew"
		)
		self.counter_name_error = ctk.CTkLabel(
			form,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.counter_name_error.grid(row=9, column=0, padx=16, sticky="ew")
		ctk.CTkLabel(
			form,
			text="Confirm Password",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=7, column=1, padx=16, pady=(5, 2), sticky="ew")
		self.counter_password_confirm_entry = ctk.CTkEntry(
			form,
			placeholder_text="Re-enter the counter password",
			show="*",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_password_confirm_entry.grid(
			row=8, column=1, padx=16, pady=(0, 8), sticky="ew"
		)
		self.counter_password_confirm_error = ctk.CTkLabel(
			form,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.counter_password_confirm_error.grid(row=9, column=1, padx=16, sticky="ew")
		ctk.CTkButton(
			form,
			text="Create Counter",
			command=self._create_counter_account,
			font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=10, column=0, padx=16, pady=(0, 8), sticky="ew")
		ctk.CTkLabel(
			form,
			text="The entered window is linked to this account’s username and password.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="w",
		).grid(row=11, column=0, columnspan=2, padx=16, pady=(0, 2), sticky="ew")
		ctk.CTkButton(
			form,
			text="Open Password Map",
			command=self._request_password_map_access,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
		).grid(row=10, column=1, padx=16, pady=(0, 12), sticky="ew")
		self.counter_account_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
		self.counter_account_list.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
		self.counter_number_error = ctk.CTkLabel(
			form,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.counter_number_error.grid(row=3, column=0, padx=16, sticky="ew")
		self._refresh_counter_accounts()

	def _validate_counter_creation(self, show_required: bool = True) -> bool:
		number_text = self.counter_number_entry.get().strip()
		number_error = ""
		if number_text and not re.fullmatch(r"\d+", number_text):
			number_error = "Enter a whole number from 1 to 100."
		elif number_text and int(number_text) > MAX_COUNTERS:
			number_error = f"Not more than {MAX_COUNTERS}."
		elif number_text and int(number_text) < 1:
			number_error = "Must be at least 1."
		elif show_required and not number_text:
			number_error = "Counter number is required."
		set_field_error(self.counter_number_entry, self.counter_number_error, number_error)

		name_error = (
			"Window name is required."
			if show_required and not self.counter_name_entry.get().strip()
			else ""
		)
		set_field_error(self.counter_name_entry, self.counter_name_error, name_error)

		prefix = self.counter_prefix_entry.get().strip()
		prefix_error = ""
		if len(prefix) > 6:
			prefix_error = "Not more than 6 characters."
		elif prefix and not re.fullmatch(r"[A-Za-z0-9]+", prefix):
			prefix_error = "Use letters and numbers only."
		elif show_required and not prefix:
			prefix_error = "Ticket prefix is required."
		set_field_error(self.counter_prefix_entry, self.counter_prefix_error, prefix_error)

		username_error = (
			"Counter username is required."
			if show_required and not self.counter_username_entry.get().strip()
			else ""
		)
		set_field_error(
			self.counter_username_entry, self.counter_username_error, username_error
		)

		password = self.counter_password_entry.get()
		password_error = (
			"Use at least 8 characters."
			if password and len(password) < 8
			else "Password is required."
			if show_required and not password
			else ""
		)
		set_field_error(self.counter_password_entry, self.counter_password_error, password_error)

		confirmation = self.counter_password_confirm_entry.get()
		confirm_error = (
			"Passwords do not match."
			if confirmation and confirmation != password
			else "Confirm the password."
			if show_required and not confirmation
			else ""
		)
		set_field_error(
			self.counter_password_confirm_entry,
			self.counter_password_confirm_error,
			confirm_error,
		)
		return not any(
			(
				number_error,
				name_error,
				prefix_error,
				username_error,
				password_error,
				confirm_error,
			)
		)

	def _create_counter_account(self) -> None:
		if not self._validate_counter_creation():
			return
		password = self.counter_password_entry.get()
		counter_number_text = self.counter_number_entry.get().strip()
		counter_number = int(counter_number_text)
		counter_name = self.counter_name_entry.get().strip()
		try:
			counter_number = create_counter_account(
				counter_name,
				self.counter_prefix_entry.get(),
				self.counter_username_entry.get(),
				password,
				counter_number,
			)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Counter creation failed", str(error), parent=self)
			return
		for entry in (
			self.counter_number_entry,
			self.counter_name_entry,
			self.counter_prefix_entry,
			self.counter_username_entry,
			self.counter_password_entry,
			self.counter_password_confirm_entry,
		):
			entry.delete(0, "end")
		self.status.set(f"{format_counter_label(counter_number, counter_name)} created.")
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
				fg_color=SOFT_GREEN,
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
		for row, (number, name, prefix, username) in enumerate(
			sorted(counters, key=lambda counter: counter[0])
		):
			card = ctk.CTkFrame(
				self.counter_account_list,
				fg_color=SURFACE,
				border_width=1,
				border_color=SOFT_BORDER,
				corner_radius=6,
			)
			card.grid(row=row, column=0, padx=5, pady=4, sticky="ew")
			card.grid_columnconfigure(0, weight=1)
			card.grid_columnconfigure(1, weight=0)
			card.grid_columnconfigure(2, weight=0)
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
				text="Edit",
				width=76,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
				fg_color=SOFT_GREEN,
				hover_color=SOFT_GREEN_HOVER,
				text_color=INK,
				command=lambda key=number, label=name, fixed_prefix=prefix, user=username: self._edit_counter_account(
					key, label, fixed_prefix, user
				),
			).grid(row=0, column=1, rowspan=2, padx=(8, 4), pady=8)
			ctk.CTkButton(
				card,
				text="Delete User",
				width=96,
				font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
				fg_color="#A64C42",
				hover_color="#873C34",
				command=lambda key=number, label=name, user=username: self._delete_counter_account(
					key, label, user
				),
			).grid(row=0, column=2, rowspan=2, padx=(4, 12), pady=8)

	def _edit_counter_account(
		self,
		counter_number: int,
		counter_name: str,
		prefix: str,
		username: str,
	) -> None:
		window = ctk.CTkToplevel(self)
		window.title(f"Edit {format_counter_label(counter_number, counter_name)}")
		window.geometry("460x620")
		window.minsize(420, 560)
		window.transient(self.winfo_toplevel())
		window.grab_set()
		set_window_icon(window)
		window.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			window,
			text="EDIT COUNTER ACCOUNT",
			font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, padx=22, pady=(20, 8), sticky="w")
		ctk.CTkLabel(
			window,
			text="Leave both password fields blank to keep the current password.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			wraplength=400,
		).grid(row=1, column=0, padx=22, pady=(0, 10), sticky="w")

		fields = (
			("Counter Name", counter_name, ""),
			("Fixed Prefix", prefix, ""),
			("Counter Username", username, ""),
			("New Password (optional)", "", "*"),
			("Confirm New Password", "", "*"),
		)
		entries = []
		errors = []
		for index, (label, value, mask) in enumerate(fields):
			row = 2 + index * 3
			ctk.CTkLabel(
				window,
				text=label,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
				text_color=INK,
				anchor="w",
			).grid(row=row, column=0, padx=22, pady=(2, 1), sticky="ew")
			entry = ctk.CTkEntry(
				window,
				show=mask,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			)
			entry.grid(row=row + 1, column=0, padx=22, pady=(0, 1), sticky="ew")
			if value:
				entry.insert(0, value)
			entries.append(entry)
			feedback = ctk.CTkLabel(
				window,
				text="",
				font=ctk.CTkFont(family=FONT_FAMILY, size=10),
				text_color="#A64C42",
				anchor="w",
			)
			feedback.grid(row=row + 2, column=0, padx=22, pady=(0, 1), sticky="ew")
			errors.append(feedback)

		name_entry, prefix_entry, username_entry, password_entry, confirm_entry = entries
		name_error, prefix_error, username_error, password_error, confirm_error = errors

		def validate_edit_form(show_required: bool = True) -> bool:
			name_message = (
				"Window name is required."
				if show_required and not name_entry.get().strip()
				else ""
			)
			set_field_error(name_entry, name_error, name_message)

			prefix = prefix_entry.get().strip()
			prefix_message = ""
			if len(prefix) > 6:
				prefix_message = "Not more than 6 characters."
			elif prefix and not re.fullmatch(r"[A-Za-z0-9]+", prefix):
				prefix_message = "Use letters and numbers only."
			elif show_required and not prefix:
				prefix_message = "Ticket prefix is required."
			set_field_error(prefix_entry, prefix_error, prefix_message)

			username_message = (
				"Counter username is required."
				if show_required and not username_entry.get().strip()
				else ""
			)
			set_field_error(username_entry, username_error, username_message)

			password = password_entry.get()
			password_message = (
				"Use at least 8 characters."
				if password and len(password) < 8
				else ""
			)
			set_field_error(password_entry, password_error, password_message)

			confirmation = confirm_entry.get()
			confirm_message = (
				"Passwords do not match."
				if confirmation and confirmation != password
				else "Confirm the new password."
				if show_required and password and not confirmation
				else ""
			)
			set_field_error(confirm_entry, confirm_error, confirm_message)
			return not any(
				(
					name_message,
					prefix_message,
					username_message,
					password_message,
					confirm_message,
				)
			)

		def save_changes() -> None:
			password = password_entry.get()
			if not validate_edit_form():
				return
			try:
				updated = update_counter_account(
					counter_number,
					name_entry.get(),
					prefix_entry.get(),
					username_entry.get(),
					password or None,
				)
			except (psycopg2.Error, ValueError) as error:
				messagebox.showerror("Counter update failed", str(error), parent=window)
				return
			if not updated:
				messagebox.showerror(
					"Counter not found",
					"This counter account no longer exists. Refresh the counter list.",
					parent=window,
				)
				window.destroy()
				self._refresh_counter_accounts()
				self._on_counters_changed()
				return
			window.destroy()
			self.status.set(f"Counter {counter_number} credentials updated.")
			self._refresh_counter_accounts()
			self._on_counters_changed()

		buttons = ctk.CTkFrame(window, fg_color="transparent")
		buttons.grid(row=17, column=0, padx=22, pady=(8, 14), sticky="ew")
		buttons.grid_columnconfigure((0, 1), weight=1)
		ctk.CTkButton(
			buttons,
			text="Save Changes",
			command=save_changes,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=0, column=0, padx=(0, 5), sticky="ew")
		ctk.CTkButton(
			buttons,
			text="Cancel",
			command=window.destroy,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			fg_color=SOFT_GREEN,
			hover_color=SOFT_GREEN_HOVER,
			text_color=INK,
		).grid(row=0, column=1, padx=(5, 0), sticky="ew")

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
