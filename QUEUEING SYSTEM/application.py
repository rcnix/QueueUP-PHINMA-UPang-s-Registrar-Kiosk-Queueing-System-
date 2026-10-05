import customtkinter as ctk
import tkinter.messagebox as messagebox
import psycopg2

from assets import center_window, set_window_icon
from database.queries import (
	admin_exists,
	authenticate_application_user,
	authenticate_kiosk_user,
	create_first_admin,
)


class AdminAccessFrame(ctk.CTkFrame):
	def __init__(self, parent, on_login, on_signup):
		super().__init__(parent, corner_radius=0, fg_color="#E8F3E8")
		self.on_login = on_login
		self.on_signup = on_signup
		self.pack(fill="both", expand=True)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)
		self._build_form()

	def _build_form(self) -> None:
		for child in self.winfo_children():
			child.destroy()
		self.panel = ctk.CTkFrame(self, width=410, fg_color="#F7FBF6", corner_radius=8)
		self.panel.grid(row=0, column=0, padx=24, pady=24)
		self.panel.grid_columnconfigure(0, weight=1)
		try:
			self.has_admin = admin_exists()
		except psycopg2.Error as error:
			messagebox.showerror("Database unavailable", str(error), parent=self)
			return
		ctk.CTkLabel(
			self.panel,
			text="QueueUP",
			font=ctk.CTkFont(family="Bahnschrift", size=24, weight="bold"),
			text_color="#183B22",
		).grid(row=0, column=0, padx=28, pady=(28, 4))
		ctk.CTkLabel(
			self.panel,
			text="Welcome to QueueUP! Please log in to continue."
			if self.has_admin else "No admin account found. Please create one.",
			font=ctk.CTkFont(family="Bahnschrift", size=13),
			text_color="#397A45",
		).grid(row=1, column=0, padx=28, pady=(0, 10))
		self.account_type = ctk.StringVar(value="Admin")
		self.account_type_switch = ctk.CTkFrame(self.panel, fg_color="transparent")
		self.account_type_switch.grid(row=2, column=0, padx=28, pady=6, sticky="ew")
		self.account_type_buttons = {}
		for column, account_type in enumerate(("Admin", "Counter User", "Kiosk User")):
			self.account_type_switch.grid_columnconfigure(column, weight=1)
			button = ctk.CTkButton(
				self.account_type_switch,
				text=account_type,
				command=lambda selected=account_type: self._on_account_type_changed(selected),
				font=ctk.CTkFont(family="Bahnschrift", size=12, weight="bold"),
				height=36,
				corner_radius=6,
				border_width=1,
				border_color="#397A45",
			)
			button.grid(row=0, column=column, padx=2, sticky="ew")
			self.account_type_buttons[account_type] = button
		self.username_entry = ctk.CTkEntry(
			self.panel,
			placeholder_text="e.g. username",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.username_entry.grid(row=3, column=0, padx=28, pady=7)
		self.password_entry = ctk.CTkEntry(
			self.panel,
			placeholder_text="Enter your password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_entry.grid(row=4, column=0, padx=28, pady=7)
		ctk.CTkButton(
			self.panel,
			text="Log In",
			command=self._submit,
			width=320,
			height=42,
			font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
			fg_color="#397A45",
			hover_color="#2F6639",
		).grid(row=5, column=0, padx=28, pady=(12, 10))
		self.signup_link = ctk.CTkLabel(
			self.panel,
			text="Create an admin account",
			font=ctk.CTkFont(family="Bahnschrift", size=12, underline=True),
			text_color="#397A45",
			cursor="hand2",
		)
		self.signup_link.grid(row=6, column=0, padx=28, pady=(0, 20))
		self._on_account_type_changed("Admin")
		self.password_entry.bind("<Return>", lambda _event: self._submit())

	def _on_account_type_changed(self, account_type: str) -> None:
		self.account_type.set(account_type)
		for button_name, button in self.account_type_buttons.items():
			selected = button_name == account_type
			button.configure(
				fg_color="#2F6639" if selected else "#E8F3E8",
				hover_color="#183B22" if selected else "#D6E9D7",
				text_color="white" if selected else "#183B22",
			)
		if account_type == "Admin":
			self.signup_link.configure(
				text="Create an admin account",
				text_color="#397A45",
				cursor="hand2",
			)
			self.signup_link.bind("<Button-1>", lambda _event: self.on_signup())
		elif account_type == "Counter User":
			self.signup_link.configure(
				text="Counter accounts are created by an admin",
				text_color="#52765A",
				cursor="arrow",
			)
			self.signup_link.unbind("<Button-1>")
		else:
			self.signup_link.configure(
				text="Kiosk credentials are configured by an admin",
				text_color="#52765A",
				cursor="arrow",
			)
			self.signup_link.unbind("<Button-1>")

	def _submit(self) -> None:
		username = self.username_entry.get().strip()
		password = self.password_entry.get()
		account_type = self.account_type.get()
		try:
			if account_type == "Kiosk User":
				authenticated = authenticate_kiosk_user(username, password)
				if not authenticated:
					messagebox.showerror(
						"Sign-in failed",
						"Invalid kiosk username or password. Ask an admin to configure kiosk access.",
						parent=self,
					)
					return
				self.on_login("kiosk", None)
				return
			role = "admin" if account_type == "Admin" else "counter"
			authenticated_user = authenticate_application_user(username, password, role)
			if authenticated_user is None:
				messagebox.showerror("Sign-in failed!", "INVALID USERNAME OR PASSWORD!", parent=self)
				return
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Sign-in failed", str(error), parent=self)
			return
		self.on_login(*authenticated_user)


class AdminRegistrationWindow(ctk.CTkToplevel):
	def __init__(self, parent, on_return):
		super().__init__(parent)
		self.parent = parent
		self.on_return = on_return
		self.title("Create Admin Account")
		self.geometry("480x600")
		self.resizable(False, False)
		set_window_icon(self)
		self.protocol("WM_DELETE_WINDOW", self._return_to_login)
		center_window(self)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)
		panel = ctk.CTkFrame(self, width=410, fg_color="#F7FBF6", corner_radius=8)
		panel.grid(row=0, column=0, padx=24, pady=24)
		panel.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			panel,
			text="Create Admin Account",
			font=ctk.CTkFont(family="Bahnschrift", size=22, weight="bold"),
			text_color="#183B22",
		).grid(row=0, column=0, padx=28, pady=(28, 8))
		ctk.CTkLabel(
			panel,
			text="Admin access is limited to the first account.",
			font=ctk.CTkFont(family="Bahnschrift", size=12),
			text_color="#397A45",
		).grid(row=1, column=0, padx=24, pady=(0, 16))
		self.username_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Username",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.username_entry.grid(row=2, column=0, padx=28, pady=7)
		self.password_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Password (8+ characters)",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_entry.grid(row=3, column=0, padx=28, pady=7)
		self.password_feedback = ctk.CTkLabel(
			panel,
			text="Weak Password",
			font=ctk.CTkFont(family="Bahnschrift", size=12, weight="bold"),
			text_color="#A64C42",
			anchor="w",
		)
		self.password_feedback.grid(row=4, column=0, padx=28, pady=(0, 1), sticky="w")
		self.password_requirements = ctk.CTkLabel(
			panel,
			text="✗ 8+ characters   ✗ uppercase   ✗ lowercase   ✗ number   ✗ symbol",
			font=ctk.CTkFont(family="Bahnschrift", size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.password_requirements.grid(row=5, column=0, padx=28, pady=(0, 4), sticky="w")
		self.confirm_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Confirm password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.confirm_entry.grid(row=6, column=0, padx=28, pady=7)
		self.confirm_feedback = ctk.CTkLabel(
			panel,
			text="",
			font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
			anchor="w",
		)
		self.confirm_feedback.grid(row=7, column=0, padx=28, pady=(0, 2), sticky="w")
		self.password_entry.bind("<KeyRelease>", self._update_password_feedback)
		self.confirm_entry.bind("<KeyRelease>", self._update_password_feedback)
		ctk.CTkButton(
			panel,
			text="Create Admin Account!",
			command=self._create_admin,
			width=320,
			height=42,
			font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
			fg_color="#397A45",
			hover_color="#2F6639",
		).grid(row=8, column=0, padx=28, pady=(12, 8))
		ctk.CTkButton(
			panel,
			text="Back to Log In",
			command=self._return_to_login,
			width=320,
			fg_color="transparent",
			text_color="#397A45",
			hover_color="#E8F3E8",
		).grid(row=9, column=0, padx=28, pady=(0, 24))

	def _update_password_feedback(self, _event=None) -> None:
		password = self.password_entry.get()
		checks = (
			(len(password) >= 8, "8+ characters"),
			(any(char.isupper() for char in password), "uppercase"),
			(any(char.islower() for char in password), "lowercase"),
			(any(char.isdigit() for char in password), "number"),
			(any(not char.isalnum() for char in password), "symbol"),
		)
		is_strong = all(passed for passed, _label in checks)
		color = "#397A45" if is_strong else "#A64C42"
		self.password_feedback.configure(
			text="Strong Password" if is_strong else "Weak Password",
			text_color=color,
		)
		self.password_requirements.configure(
			text="   ".join(
				f"{'✓' if passed else '✗'} {label}" for passed, label in checks
			),
			text_color=color,
		)
		confirmation = self.confirm_entry.get()
		if not confirmation:
			self.confirm_feedback.configure(text="", text_color="#52765A")
		elif confirmation == password:
			self.confirm_feedback.configure(text="Password Match!", text_color="#397A45")
		else:
			self.confirm_feedback.configure(
				text="Passwords do not match", text_color="#A64C42"
			)

	def _create_admin(self) -> None:
		username = self.username_entry.get().strip()
		password = self.password_entry.get()
		if len(password) < 8:
			messagebox.showwarning("Password too Short!", "Use at least 8 characters!", parent=self)
			return
		if password != self.confirm_entry.get():
			messagebox.showwarning("Passwords do not match!", "Enter the same password twice!", parent=self)
			return
		try:
			create_first_admin(username, password)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Admin creation failed!", str(error), parent=self)
			return
		messagebox.showinfo("USER ADMIN CREATED", "USER ADMIN CREATED", parent=self)
		self._return_to_login()

	def _return_to_login(self) -> None:
		self.destroy()
		self.parent.deiconify()
		self.on_return()


class QueueUPApp(ctk.CTk):
	def __init__(self) -> None:
		super().__init__()
		self.title("QueueUP Login")
		set_window_icon(self)
		self._active_view = None
		self._registration_window = None
		self.show_login()

	def _clear_view(self) -> None:
		if self._active_view is not None:
			self._active_view.destroy()
			self._active_view = None

	def show_login(self) -> None:
		self._clear_view()
		self.title("QueueUP Login")
		self.geometry("480x440")
		self.minsize(480, 440)
		self.maxsize(480, 440)
		self.resizable(False, False)
		self._active_view = AdminAccessFrame(
			self, self._route_authenticated_user, self.show_registration
		)
		self.update_idletasks()
		center_window(self)

	def _route_authenticated_user(
		self,
		role: str,
		counter_number: int | None,
	) -> None:
		if role == "admin":
			self.show_admin()
		elif role == "counter" and counter_number is not None:
			self.show_counter(counter_number)
		elif role == "kiosk":
			self.show_kiosk()
		else:
			messagebox.showerror(
				"Sign-in failed",
				"This account is not assigned to an active counter.",
				parent=self,
			)

	def show_registration(self) -> None:
		if self._registration_window is not None and self._registration_window.winfo_exists():
			self._registration_window.lift()
			return
		self._registration_window = AdminRegistrationWindow(self, self.show_login)
		self._registration_window.deiconify()
		self._registration_window.update()
		self.iconify()
		self._registration_window.deiconify()
		self._registration_window.lift()

	def show_admin(self) -> None:
		self._clear_view()
		self.title("QueueUP Admin")
		self.minsize(850, 560)
		self.maxsize(10000, 10000)
		self.resizable(True, True)
		self.geometry("1200x800")
		self.update_idletasks()
		center_window(self)
		from admin.dashboard import AdminDashboard

		self._active_view = AdminDashboard(
			self,
			on_logout=self.show_login,
			on_delete_account=self.show_login,
		)

	def show_counter(self, counter_number: int) -> None:
		self._clear_view()
		self.title(f"QueueUP - Counter {counter_number}")
		self.minsize(540, 480)
		self.maxsize(10000, 10000)
		self.resizable(True, True)
		self.geometry("700x600")
		self.update_idletasks()
		center_window(self)
		from counter.counter_window import CounterWindow

		self._active_view = CounterWindow(
			self,
			counter_number,
			on_logout=self.show_login,
		)

	def show_kiosk(self) -> None:
		self._clear_view()
		self.title("QueueUP - Get a Ticket")
		self.minsize(800, 740)
		self.maxsize(10000, 10000)
		self.resizable(True, True)
		self.geometry("980x900")
		self.update_idletasks()
		center_window(self)
		from kiosk.kiosk_window import KioskWindow

		self._active_view = KioskWindow(self)
		self._active_view.pack(fill="both", expand=True)