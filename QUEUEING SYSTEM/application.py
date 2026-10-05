import customtkinter as ctk
import tkinter.messagebox as messagebox
import psycopg2

from assets import center_window, set_window_icon
from database.queries import admin_exists, authenticate, create_first_admin


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
			text="QueueUP Admin",
			font=ctk.CTkFont(family="Bahnschrift", size=24, weight="bold"),
			text_color="#183B22",
		).grid(row=0, column=0, padx=28, pady=(28, 4))
		ctk.CTkLabel(
			self.panel,
			text="Sign in to continue",
			font=ctk.CTkFont(family="Bahnschrift", size=13),
			text_color="#397A45",
		).grid(row=1, column=0, padx=28, pady=(0, 18))
		self.username_entry = ctk.CTkEntry(
			self.panel,
			placeholder_text="Username",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.username_entry.grid(row=2, column=0, padx=28, pady=7)
		self.password_entry = ctk.CTkEntry(
			self.panel,
			placeholder_text="Password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_entry.grid(row=3, column=0, padx=28, pady=7)
		ctk.CTkButton(
			self.panel,
			text="Log In",
			command=self._submit,
			width=320,
			height=42,
			font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
			fg_color="#397A45",
			hover_color="#2F6639",
		).grid(row=4, column=0, padx=28, pady=(16, 12))
		self.signup_link = ctk.CTkLabel(
			self.panel,
			text="Running as Admin?",
			font=ctk.CTkFont(family="Bahnschrift", size=12, underline=True),
			text_color="#397A45",
			cursor="hand2",
		)
		self.signup_link.grid(row=5, column=0, padx=28, pady=(0, 24))
		self.signup_link.bind("<Button-1>", lambda _event: self.on_signup())
		self.password_entry.bind("<Return>", lambda _event: self._submit())

	def _submit(self) -> None:
		username = self.username_entry.get().strip()
		password = self.password_entry.get()
		try:
			if not authenticate(username, password, role="admin"):
				messagebox.showerror("Sign-in failed", "Invalid username or password.", parent=self)
				return
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Sign-in failed", str(error), parent=self)
			return
		self.on_login()


class AdminRegistrationWindow(ctk.CTkToplevel):
	def __init__(self, parent, on_return):
		super().__init__(parent)
		self.parent = parent
		self.on_return = on_return
		self.title("Create Admin Account")
		self.geometry("480x500")
		self.resizable(False, False)
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
		self.confirm_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Confirm password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.confirm_entry.grid(row=4, column=0, padx=28, pady=7)
		ctk.CTkButton(
			panel,
			text="Create Admin",
			command=self._create_admin,
			width=320,
			height=42,
			font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
			fg_color="#397A45",
			hover_color="#2F6639",
		).grid(row=5, column=0, padx=28, pady=(16, 8))
		ctk.CTkButton(
			panel,
			text="Back to Log In",
			command=self._return_to_login,
			width=320,
			fg_color="transparent",
			text_color="#397A45",
			hover_color="#E8F3E8",
		).grid(row=6, column=0, padx=28, pady=(0, 24))

	def _create_admin(self) -> None:
		username = self.username_entry.get().strip()
		password = self.password_entry.get()
		if len(password) < 8:
			messagebox.showwarning("Password too short", "Use at least 8 characters.", parent=self)
			return
		if password != self.confirm_entry.get():
			messagebox.showwarning("Passwords do not match", "Enter the same password twice.", parent=self)
			return
		try:
			create_first_admin(username, password)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Admin creation failed", str(error), parent=self)
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
		self.title("QueueUP Admin")
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
		self.title("QueueUP Admin Login")
		self.geometry("480x390")
		self.minsize(480, 390)
		self.maxsize(480, 390)
		self.resizable(False, False)
		self._active_view = AdminAccessFrame(self, self.show_admin, self.show_registration)
		self.update_idletasks()
		center_window(self)

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