import customtkinter as ctk
import tkinter.messagebox as messagebox
import psycopg2

from admin.validation import set_field_error, set_field_state
from admin.email_verification import issue_and_send_admin_code
from admin.styles import (
	BORDER,
	GREEN,
	GREEN_HOVER,
	HOVER_GREEN,
	INK,
	MUTED_GREEN,
	PALE_GREEN,
	SOFT_GREEN,
	SURFACE,
)
from assets import center_window, format_counter_label, set_window_icon
from database.queries import (
	admin_exists,
	authenticate_application_user,
	authenticate_kiosk_user,
	complete_admin_email_update,
	complete_admin_recovery,
	complete_admin_signup,
)


def _strong_admin_password(password: str) -> bool:
	return all(
		(
			len(password) >= 8,
			any(char.isupper() for char in password),
			any(char.islower() for char in password),
			any(char.isdigit() for char in password),
			any(not char.isalnum() for char in password),
		)
	)


class AdminAccessFrame(ctk.CTkFrame):
	def __init__(self, parent, on_login, on_signup, on_forgot):
		super().__init__(parent, corner_radius=0, fg_color=PALE_GREEN)
		self.on_login = on_login
		self.on_signup = on_signup
		self.on_forgot = on_forgot
		self.pack(fill="both", expand=True)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)
		self._build_form()

	def _build_form(self) -> None:
		for child in self.winfo_children():
			child.destroy()
		self.panel = ctk.CTkFrame(self, width=410, fg_color=SURFACE, corner_radius=8)
		self.panel.grid(row=0, column=0, padx=14, pady=12)
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
			text_color=INK,
		).grid(row=0, column=0, padx=16, pady=(12, 4))
		ctk.CTkLabel(
			self.panel,
			text="Welcome to QueueUP! Please log in to continue."
			if self.has_admin else "No admin account found. Please create one.",
			font=ctk.CTkFont(family="Bahnschrift", size=13),
			text_color=GREEN,
		).grid(row=1, column=0, padx=16, pady=(0, 6))
		self.account_type = ctk.StringVar(value="Admin")
		self.account_type_switch = ctk.CTkFrame(self.panel, fg_color="transparent")
		self.account_type_switch.grid(row=2, column=0, padx=16, pady=3, sticky="ew")
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
				border_color=GREEN,
			)
			button.grid(row=0, column=column, padx=2, sticky="ew")
			self.account_type_buttons[account_type] = button
		self.username_entry = ctk.CTkEntry(
			self.panel,
			placeholder_text="Username or admin email",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.username_entry.grid(row=3, column=0, padx=16, pady=2)
		self.password_frame = ctk.CTkFrame(self.panel, fg_color="transparent")
		self.password_frame.grid(row=4, column=0, padx=16, pady=2, sticky="ew")
		self.password_frame.grid_columnconfigure(0, weight=1)
		self.password_entry = ctk.CTkEntry(
			self.password_frame,
			placeholder_text="Enter your password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._login_show_password = False
		self.show_login_password_btn = ctk.CTkButton(
			self.password_frame,
			text="✭",
			width=30,
			command=self._toggle_login_password_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_login_password_btn.grid(row=0, column=1)
		ctk.CTkButton(
			self.panel,
			text="Log In",
			command=self._submit,
			width=320,
			height=42,
			font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=5, column=0, padx=16, pady=(4, 4))
		self.signup_link = ctk.CTkLabel(
			self.panel,
			text="Create an admin account",
			font=ctk.CTkFont(family="Bahnschrift", size=12, underline=True),
			text_color=GREEN,
			cursor="hand2",
		)
		self.signup_link.grid(row=6, column=0, padx=16, pady=(4, 2))
		self.forgot_link = ctk.CTkLabel(
			self.panel,
			text="Forgot username or password?",
			font=ctk.CTkFont(family="Bahnschrift", size=12, underline=True),
			text_color=GREEN,
			cursor="hand2",
		)
		self.forgot_link.grid(row=7, column=0, padx=16, pady=(2, 14))
		self.forgot_link.bind("<Button-1>", lambda _event: self.on_forgot())
		self._on_account_type_changed("Admin")
		self.password_entry.bind("<Return>", lambda _event: self._submit())

	def _on_account_type_changed(self, account_type: str) -> None:
		self.account_type.set(account_type)
		for button_name, button in self.account_type_buttons.items():
			selected = button_name == account_type
			button.configure(
				fg_color=GREEN_HOVER if selected else PALE_GREEN,
				hover_color=INK if selected else HOVER_GREEN,
				text_color="#FFFFFF" if selected else INK,
			)
		if account_type == "Admin":
			if self.has_admin:
				self.signup_link.configure(
					text="An admin account already exists",
					text_color=MUTED_GREEN,
					cursor="arrow",
				)
				self.signup_link.unbind("<Button-1>")
			else:
				self.signup_link.configure(
					text="Create an admin account",
					text_color=GREEN,
					cursor="hand2",
				)
				self.signup_link.bind("<Button-1>", lambda _event: self.on_signup())
		elif account_type == "Counter User":
			self.signup_link.configure(
				text="Counter accounts are created by an admin",
				text_color=MUTED_GREEN,
				cursor="arrow",
			)
			self.signup_link.unbind("<Button-1>")
			self.forgot_link.grid_remove()
		else:
			self.signup_link.configure(
				text="Kiosk credentials are configured by an admin",
				text_color=MUTED_GREEN,
				cursor="arrow",
			)
			self.signup_link.unbind("<Button-1>")
			self.forgot_link.grid_remove()
		if account_type == "Admin":
			self.forgot_link.grid()

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
				self.on_login("kiosk", None, None)
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

	def _toggle_login_password_visibility(self) -> None:
		self._login_show_password = not self._login_show_password
		self.password_entry.configure(show="" if self._login_show_password else "*")
		self.show_login_password_btn.configure(
			text="⭑" if self._login_show_password else "✭"
		)


class AdminRegistrationWindow(ctk.CTkToplevel):
	def __init__(self, parent, on_return):
		super().__init__(parent)
		self.parent = parent
		self.on_return = on_return
		self.title("Create Admin Account")
		self.geometry("480x640")
		self.resizable(False, False)
		set_window_icon(self)
		self.protocol("WM_DELETE_WINDOW", self._return_to_login)
		center_window(self)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)
		panel = ctk.CTkFrame(self, width=410, fg_color=SURFACE, corner_radius=8)
		panel.grid(row=0, column=0, padx=14, pady=12)
		panel.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			panel,
			text="Create Admin Account",
			font=ctk.CTkFont(family="Bahnschrift", size=22, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, padx=16, pady=(10, 4))
		ctk.CTkLabel(
			panel,
			text="Admin access is limited to the first account.",
			font=ctk.CTkFont(family="Bahnschrift", size=12),
			text_color=GREEN,
		).grid(row=1, column=0, padx=16, pady=(0, 6))
		self.username_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Username",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.username_entry.grid(row=2, column=0, padx=16, pady=2)
		self.username_error = ctk.CTkLabel(
			panel,
			text="",
			font=ctk.CTkFont(family="Bahnschrift", size=10),
			text_color="#A64C42",
			anchor="w",
		)
		self.username_error.grid(row=3, column=0, padx=16, sticky="w")
		self.username_error.grid_remove()
		self.email_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Admin email address",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.email_entry.grid(row=4, column=0, padx=16, pady=2)
		self.password_frame = ctk.CTkFrame(panel, fg_color="transparent")
		self.password_frame.grid(row=5, column=0, padx=16, pady=2, sticky="ew")
		self.password_frame.grid_columnconfigure(0, weight=1)
		self.password_entry = ctk.CTkEntry(
			self.password_frame,
			placeholder_text="Password (8+ characters)",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._reg_show_password = False
		self.show_reg_password_btn = ctk.CTkButton(
			self.password_frame,
			text="✭",
			width=30,
			command=self._toggle_reg_password_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_reg_password_btn.grid(row=0, column=1)
		self.password_feedback = ctk.CTkLabel(
			panel,
			text="",
			font=ctk.CTkFont(family="Bahnschrift", size=12, weight="bold"),
			text_color=MUTED_GREEN,
			anchor="w",
		)
		self.password_feedback.grid(row=6, column=0, padx=16, pady=(3, 1), sticky="w")
		self.password_feedback.grid_remove()
		self.password_requirements = ctk.CTkLabel(
			panel,
			text="",
			font=ctk.CTkFont(family="Bahnschrift", size=10),
			text_color=MUTED_GREEN,
			anchor="w",
		)
		self.password_requirements.grid(row=7, column=0, padx=16, pady=(1, 1), sticky="w")
		self.password_requirements.grid_remove()
		self.confirm_frame = ctk.CTkFrame(panel, fg_color="transparent")
		self.confirm_frame.grid(row=8, column=0, padx=16, pady=2, sticky="ew")
		self.confirm_frame.grid_columnconfigure(0, weight=1)
		self.confirm_entry = ctk.CTkEntry(
			self.confirm_frame,
			placeholder_text="Confirm password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.confirm_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._reg_show_confirm = False
		self.show_reg_confirm_btn = ctk.CTkButton(
			self.confirm_frame,
			text="✭",
			width=30,
			command=self._toggle_reg_confirm_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_reg_confirm_btn.grid(row=0, column=1)
		self.confirm_feedback = ctk.CTkLabel(
			panel,
			text="",
			font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
			anchor="w",
		)
		self.confirm_feedback.grid(row=10, column=0, padx=16, pady=(2, 1), sticky="w")
		self.confirm_feedback.grid_remove()
		self.send_code_button = ctk.CTkButton(
			panel,
			text="Send email verification code",
			command=self._send_signup_code,
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		)
		self.send_code_button.grid(row=11, column=0, padx=16, pady=(3, 3))
		self.verification_entry = ctk.CTkEntry(
			panel,
			placeholder_text="6-digit verification code",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.verification_entry.grid(row=12, column=0, padx=16, pady=2)
		self.signup_status = ctk.CTkLabel(
			panel,
			text="",
			font=ctk.CTkFont(family="Bahnschrift", size=11),
			text_color=GREEN,
			wraplength=320,
		)
		self.signup_status.grid(row=13, column=0, padx=16, pady=(2, 1))
		self.signup_status.grid_remove()
		ctk.CTkButton(
			panel,
			text="Verify Email & Create Account",
			command=self._verify_signup_code,
			width=320,
			height=42,
			font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=14, column=0, padx=16, pady=(5, 4))
		ctk.CTkButton(
			panel,
			text="Back to Log In",
			command=self._return_to_login,
			width=320,
			fg_color="transparent",
			text_color=GREEN,
			hover_color=PALE_GREEN,
		).grid(row=15, column=0, padx=16, pady=(0, 12))
		self.password_entry.bind("<KeyRelease>", self._update_password_feedback)
		self.confirm_entry.bind("<KeyRelease>", self._update_password_feedback)

	def _toggle_reg_password_visibility(self) -> None:
		self._reg_show_password = not self._reg_show_password
		self.password_entry.configure(show="" if self._reg_show_password else "*")
		self.show_reg_password_btn.configure(
			text="⭑" if self._reg_show_password else "✭"
		)

	def _toggle_reg_confirm_visibility(self) -> None:
		self._reg_show_confirm = not self._reg_show_confirm
		self.confirm_entry.configure(show="" if self._reg_show_confirm else "*")
		self.show_reg_confirm_btn.configure(
			text="⭑" if self._reg_show_confirm else "✭"
		)

	def _update_password_feedback(self, _event=None, show_required: bool = False) -> None:
		username = self.username_entry.get().strip()
		set_field_error(
			self.username_entry,
			self.username_error,
			"Username is required." if show_required and not username else "",
		)
		password = self.password_entry.get()
		checks = (
			(len(password) >= 8, "8+ characters"),
			(any(char.isupper() for char in password), "uppercase"),
			(any(char.islower() for char in password), "lowercase"),
			(any(char.isdigit() for char in password), "number"),
			(any(not char.isalnum() for char in password), "symbol"),
		)
		is_strong = all(passed for passed, _label in checks)
		color = GREEN if is_strong else "#A64C42"
		self.password_feedback.configure(
			text="Strong Password" if is_strong else "Weak Password",
			text_color=color,
		)
		self.password_requirements.configure(
			text="  ".join(
				f"{'✓' if passed else '✗'} {label}" for passed, label in checks
			),
			text_color=color,
		)
		self.password_feedback.grid()
		self.password_requirements.grid()
		set_field_state(self.password_entry, not is_strong)
		confirmation = self.confirm_entry.get()
		if not confirmation:
			message = "Confirm your password." if show_required else ""
			self.confirm_feedback.configure(
				text=message,
				text_color="#A64C42" if message else MUTED_GREEN,
			)
			set_field_state(self.confirm_entry, bool(message))
			if message:
				self.confirm_feedback.grid()
			else:
				self.confirm_feedback.grid_remove()
		elif confirmation == password:
			self.confirm_feedback.configure(text="Password Match!", text_color=GREEN)
			set_field_state(self.confirm_entry, False)
			self.confirm_feedback.grid()
		else:
			self.confirm_feedback.configure(
				text="Passwords do not match", text_color="#A64C42"
			)
			set_field_state(self.confirm_entry, True)
			self.confirm_feedback.grid()

	def _send_signup_code(self) -> None:
		self._update_password_feedback(show_required=True)
		username = self.username_entry.get().strip()
		email = self.email_entry.get().strip()
		password = self.password_entry.get()
		strong_password = _strong_admin_password(password)
		if not username or not email:
			messagebox.showwarning(
				"Account details required",
				"Enter a username and email address.",
				parent=self,
			)
			return
		if not strong_password:
			messagebox.showwarning(
				"Weak password",
				"Use at least 8 characters and include uppercase, lowercase, a number, and a symbol.",
				parent=self,
			)
			return
		if password != self.confirm_entry.get():
			messagebox.showwarning(
				"Passwords do not match!",
				"Enter the same password twice!",
				parent=self,
			)
			return
		try:
			sent = issue_and_send_admin_code(email, "signup")
		except (OSError, psycopg2.Error, ValueError) as error:
			messagebox.showerror("Could not send verification email", str(error), parent=self)
			return
		if not sent:
			messagebox.showerror(
				"Verification unavailable",
				"An admin account already exists or this address cannot be verified.",
				parent=self,
			)
			return
		self.signup_status.configure(
			text="Code sent. Enter it within 5 minutes to create the account."
		)
		self.signup_status.grid()

	def _verify_signup_code(self) -> None:
		try:
			complete_admin_signup(
				self.username_entry.get(),
				self.email_entry.get(),
				self.password_entry.get(),
				self.verification_entry.get().strip(),
			)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Admin verification failed", str(error), parent=self)
			return
		messagebox.showinfo(
			"Admin account created",
			"Email verified and admin account created.",
			parent=self,
		)
		self._return_to_login()

	def _return_to_login(self) -> None:
		self.destroy()
		self.parent.deiconify()
		self.on_return()


class AdminRecoveryWindow(ctk.CTkToplevel):
	def __init__(self, parent, on_return):
		super().__init__(parent)
		self.parent = parent
		self.on_return = on_return
		self.title("Recover Admin Account")
		self.geometry("480x620")
		self.resizable(False, False)
		self.transient(parent)
		self.grab_set()
		set_window_icon(self)
		self.protocol("WM_DELETE_WINDOW", self._return_to_login)
		center_window(self)
		self.grid_columnconfigure(0, weight=1)
		panel = ctk.CTkFrame(self, width=410, fg_color=SURFACE, corner_radius=8)
		panel.grid(row=0, column=0, padx=14, pady=12)
		panel.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			panel,
			text="Recover Admin Account",
			font=ctk.CTkFont(family="Bahnschrift", size=21, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, padx=16, pady=(12, 4))
		ctk.CTkLabel(
			panel,
			text="A code is sent only if this email belongs to the admin.",
			font=ctk.CTkFont(family="Bahnschrift", size=11),
			text_color=GREEN,
			wraplength=330,
		).grid(row=1, column=0, padx=16, pady=(0, 6))
		self.email_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Admin email",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.email_entry.grid(row=2, column=0, padx=16, pady=4)
		ctk.CTkButton(
			panel,
			text="Send recovery code",
			command=self._send_recovery_code,
			width=320,
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=3, column=0, padx=16, pady=4)
		self.code_entry = ctk.CTkEntry(
			panel,
			placeholder_text="6-digit code",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.code_entry.grid(row=4, column=0, padx=16, pady=4)
		self.recovery_password_frame = ctk.CTkFrame(panel, fg_color="transparent")
		self.recovery_password_frame.grid(row=5, column=0, padx=16, pady=4, sticky="ew")
		self.recovery_password_frame.grid_columnconfigure(0, weight=1)
		self.password_entry = ctk.CTkEntry(
			self.recovery_password_frame,
			placeholder_text="New password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._recovery_show_password = False
		self.show_recovery_password_btn = ctk.CTkButton(
			self.recovery_password_frame,
			text="✭",
			width=30,
			command=self._toggle_recovery_password_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_recovery_password_btn.grid(row=0, column=1)
		self.recovery_confirm_frame = ctk.CTkFrame(panel, fg_color="transparent")
		self.recovery_confirm_frame.grid(row=6, column=0, padx=16, pady=4, sticky="ew")
		self.recovery_confirm_frame.grid_columnconfigure(0, weight=1)
		self.confirm_entry = ctk.CTkEntry(
			self.recovery_confirm_frame,
			placeholder_text="Confirm new password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.confirm_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._recovery_show_confirm = False
		self.show_recovery_confirm_btn = ctk.CTkButton(
			self.recovery_confirm_frame,
			text="✭",
			width=30,
			command=self._toggle_recovery_confirm_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_recovery_confirm_btn.grid(row=0, column=1)
		ctk.CTkLabel(
			panel,
			text="Password needs 8+ characters, upper/lowercase, a number, and a symbol.",
			font=ctk.CTkFont(family="Bahnschrift", size=10),
			text_color=MUTED_GREEN,
			wraplength=330,
		).grid(row=7, column=0, padx=16, pady=(2, 6))
		ctk.CTkButton(
			panel,
			text="Verify Code & Reset Password",
			command=self._reset_password,
			width=320,
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=8, column=0, padx=16, pady=4)
		self.status = ctk.CTkLabel(
			panel, text="", font=ctk.CTkFont(family="Bahnschrift", size=11),
			text_color=GREEN, wraplength=320,
		)
		self.status.grid(row=9, column=0, padx=16, pady=4)
		ctk.CTkButton(
			panel,
			text="Back to Log In",
			command=self._return_to_login,
			width=320,
			fg_color="transparent",
			text_color=GREEN,
			hover_color=PALE_GREEN,
		).grid(row=10, column=0, padx=16, pady=(4, 12))

	def _send_recovery_code(self) -> None:
		try:
			issue_and_send_admin_code(self.email_entry.get(), "recovery")
		except (OSError, psycopg2.Error, ValueError) as error:
			messagebox.showerror("Could not send recovery email", str(error), parent=self)
			return
		self.status.configure(
			text="If the email matches an admin account, a code was sent. It expires in 5 minutes."
		)

	def _reset_password(self) -> None:
		password = self.password_entry.get()
		if not _strong_admin_password(password):
			messagebox.showwarning(
				"Weak password",
				"Use 8+ characters with uppercase, lowercase, a number, and a symbol.",
				parent=self,
			)
			return
		if password != self.confirm_entry.get():
			messagebox.showwarning("Passwords do not match", "Confirm the new password.", parent=self)
			return
		try:
			username = complete_admin_recovery(
				self.email_entry.get(),
				self.code_entry.get().strip(),
				password,
			)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Account recovery failed", str(error), parent=self)
			return
		messagebox.showinfo(
			"Account recovered",
			f"Your username is {username}. You can now sign in with your new password.",
			parent=self,
		)
		self._return_to_login()

	def _return_to_login(self) -> None:
		self.destroy()
		self.parent.deiconify()
		self.on_return()

	def _toggle_recovery_password_visibility(self) -> None:
		self._recovery_show_password = not self._recovery_show_password
		self.password_entry.configure(show="" if self._recovery_show_password else "*")
		self.show_recovery_password_btn.configure(
			text="⭑" if self._recovery_show_password else "✭"
		)

	def _toggle_recovery_confirm_visibility(self) -> None:
		self._recovery_show_confirm = not self._recovery_show_confirm
		self.confirm_entry.configure(show="" if self._recovery_show_confirm else "*")
		self.show_recovery_confirm_btn.configure(
			text="⭑" if self._recovery_show_confirm else "✭"
		)


class AdminEmailUpdateWindow(ctk.CTkToplevel):
	def __init__(self, parent, on_complete):
		super().__init__(parent)
		self.on_complete = on_complete
		self.title("Set Admin Recovery Email")
		self.geometry("460x390")
		self.resizable(False, False)
		self.transient(parent.winfo_toplevel())
		self.grab_set()
		set_window_icon(self)
		center_window(self)
		self.grid_columnconfigure(0, weight=1)
		panel = ctk.CTkFrame(self, width=400, fg_color=SURFACE, corner_radius=8)
		panel.grid(row=0, column=0, padx=14, pady=12)
		panel.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			panel,
			text="Set Admin Recovery Email",
			font=ctk.CTkFont(family="Bahnschrift", size=18, weight="bold"),
			text_color=INK,
		).grid(row=0, column=0, padx=16, pady=(12, 6))
		self.email_update_password_frame = ctk.CTkFrame(panel, fg_color="transparent")
		self.email_update_password_frame.grid(row=1, column=0, padx=16, pady=4, sticky="ew")
		self.email_update_password_frame.grid_columnconfigure(0, weight=1)
		self.password_entry = ctk.CTkEntry(
			self.email_update_password_frame,
			placeholder_text="Current admin password",
			show="*",
			width=320,
		)
		self.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._email_update_show_password = False
		self.show_email_update_password_btn = ctk.CTkButton(
			self.email_update_password_frame,
			text="✭",
			width=30,
			command=self._toggle_email_update_password_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_email_update_password_btn.grid(row=0, column=1)
		self.email_entry = ctk.CTkEntry(
			panel, placeholder_text="New recovery email", width=320
		)
		self.email_entry.grid(row=2, column=0, padx=16, pady=4)
		ctk.CTkButton(
			panel,
			text="Send verification code",
			command=self._send_code,
			width=320,
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=3, column=0, padx=16, pady=4)
		self.code_entry = ctk.CTkEntry(
			panel, placeholder_text="6-digit verification code", width=320
		)
		self.code_entry.grid(row=4, column=0, padx=16, pady=4)
		ctk.CTkButton(
			panel,
			text="Verify & Save Email",
			command=self._save_email,
			width=320,
			fg_color=GREEN,
			hover_color=GREEN_HOVER,
		).grid(row=5, column=0, padx=16, pady=4)

	def _send_code(self) -> None:
		try:
			issue_and_send_admin_code(
				self.email_entry.get(),
				"email_update",
				self.password_entry.get(),
			)
		except (OSError, psycopg2.Error, ValueError) as error:
			messagebox.showerror("Could not send verification email", str(error), parent=self)

	def _save_email(self) -> None:
		try:
			complete_admin_email_update(
				self.email_entry.get(),
				self.code_entry.get().strip(),
				self.password_entry.get(),
			)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Could not update recovery email", str(error), parent=self)
			return
		messagebox.showinfo("Recovery email updated", "Your admin email is verified and saved.", parent=self)
		self.destroy()
		self.on_complete()

	def _toggle_email_update_password_visibility(self) -> None:
		self._email_update_show_password = not self._email_update_show_password
		self.password_entry.configure(show="" if self._email_update_show_password else "*")
		self.show_email_update_password_btn.configure(
			text="⭑" if self._email_update_show_password else "✭"
		)


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
		self.geometry("520x520")
		self.minsize(520, 520)
		self.maxsize(520, 520)
		self.resizable(False, False)
		self._active_view = AdminAccessFrame(
			self,
			self._route_authenticated_user,
			self.show_registration,
			self.show_recovery,
		)
		self.update_idletasks()
		center_window(self)

	def _route_authenticated_user(
		self,
		role: str,
		counter_number: int | None,
		counter_name: str | None,
	) -> None:
		if role == "admin":
			self.show_admin()
		elif role == "counter" and counter_number is not None:
			self.show_counter(counter_number, counter_name)
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
		try:
			has_admin = admin_exists()
		except psycopg2.Error as error:
			messagebox.showerror("Database unavailable", str(error), parent=self)
			return
		if has_admin:
			messagebox.showinfo(
				"Admin account exists",
				"An admin account already exists. Admin access is limited to the first account.",
				parent=self,
			)
			return
		self._registration_window = AdminRegistrationWindow(self, self.show_login)
		self._registration_window.deiconify()
		self._registration_window.update()
		self.iconify()
		self._registration_window.deiconify()
		self._registration_window.lift()

	def show_recovery(self) -> None:
		window = AdminRecoveryWindow(self, self.show_login)
		window.deiconify()
		window.lift()
		self.iconify()

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

	def show_counter(self, counter_number: int, counter_name: str | None = None) -> None:
		self._clear_view()
		self.title(
			f"QueueUP - "
			f"{format_counter_label(counter_number, counter_name or '')}"
		)
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
			counter_name,
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
