import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from admin.styles import FONT_FAMILY, GREEN, GREEN_HOVER, INK
from database.queries import create_counter_account, get_counters


class CounterCreationMixin:
	def _build_counter_creation_tab(self, tab) -> None:
		tab.grid_columnconfigure(0, weight=1)
		tab.grid_rowconfigure(2, weight=1)
		form = ctk.CTkFrame(tab, fg_color="transparent")
		form.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
		for column in range(5):
			form.grid_columnconfigure(column, weight=1)
		self.counter_name_entry = ctk.CTkEntry(
			form,
			placeholder_text="Counter name",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_name_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
		self.counter_prefix_entry = ctk.CTkEntry(
			form,
			placeholder_text="Fixed prefix",
			width=110,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_prefix_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
		self.counter_username_entry = ctk.CTkEntry(
			form,
			placeholder_text="Counter username",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_username_entry.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
		self.counter_password_entry = ctk.CTkEntry(
			form,
			placeholder_text="Password (8+ characters)",
			show="*",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_password_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
		self.counter_password_confirm_entry = ctk.CTkEntry(
			form,
			placeholder_text="Confirm password",
			show="*",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
		)
		self.counter_password_confirm_entry.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
		ctk.CTkButton(
			form,
			text="Create Counter",
			command=self._create_counter_account,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=1, column=3, padx=5, pady=5, sticky="ew")
		ctk.CTkLabel(
			tab,
			text="Each counter gets one fixed ticket prefix and one counter-only login.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="w",
		).grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")
		self.counter_account_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
		self.counter_account_list.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="nsew")
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
			ctk.CTkLabel(
				self.counter_account_list,
				text=f"COUNTER {number}  |  {name}  |  Prefix {prefix}  |  Login {username}",
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color=INK,
				anchor="w",
			).grid(row=row, column=0, padx=8, pady=6, sticky="ew")
