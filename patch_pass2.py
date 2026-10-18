path = r'c:/Users/bombie/OneDrive/Documents/PROJECT/QUEUEING SYSTEM/application.py'

with open(path, 'r') as f:
    content = f.read()

# 1. Fix registration window password entry (the first occurrence with placeholder "Password (8+ characters)")
old1 = '''		self.password_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Password (8+ characters)",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_entry.grid(row=5, column=0, padx=16, pady=4)'''

new1 = '''		self.password_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Password (8+ characters)",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.password_frame = ctk.CTkFrame(panel, fg_color="transparent")
		self.password_frame.grid(row=5, column=0, padx=16, pady=4, sticky="ew")
		self.password_frame.grid_columnconfigure(0, weight=1)
		self.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._show_password = False
		self.show_password_btn = ctk.CTkButton(
			self.password_frame,
			text="\u2605",
			width=30,
			command=self._toggle_password_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_password_btn.grid(row=0, column=1)'''

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("Registration password section patched")
else:
    print("Registration password section NOT found")

# 2. Fix registration window confirm entry (with placeholder "Confirm password")
old2 = '''		self.confirm_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Confirm password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.confirm_entry.grid(row=8, column=0, padx=16, pady=2)'''

new2 = '''		self.confirm_entry = ctk.CTkEntry(
			panel,
			placeholder_text="Confirm password",
			show="*",
			width=320,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.confirm_frame = ctk.CTkFrame(panel, fg_color="transparent")
		self.confirm_frame.grid(row=8, column=0, padx=16, pady=2, sticky="ew")
		self.confirm_frame.grid_columnconfigure(0, weight=1)
		self.confirm_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
		self._show_confirm = False
		self.show_confirm_btn = ctk.CTkButton(
			self.confirm_frame,
			text="\u2605",
			width=30,
			command=self._toggle_confirm_visibility,
			font=ctk.CTkFont(family="Bahnschrift", size=13),
		)
		self.show_confirm_btn.grid(row=0, column=1)'''

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("Registration confirm section patched")
else:
    print("Registration confirm section NOT found")

# 3. Add toggle methods before _submit
old3 = '	def _submit(self) -> None:'
new3 = '''	def _toggle_password_visibility(self) -> None:
		self._show_password = not self._show_password
		self.password_entry.configure(show="" if self._show_password else "*")
		self.show_password_btn.configure(text="\u2605" if self._show_password else "\u2606")

	def _toggle_confirm_visibility(self) -> None:
		self._show_confirm = not self._show_confirm
		self.confirm_entry.configure(show="" if self._show_confirm else "*")
		self.show_confirm_btn.configure(text="\u2605" if self._show_confirm else "\u2606")

	def _submit(self) -> None:'''

if old3 in content:
    content = content.replace(old3, new3, 1)
    print("Toggle methods added")
else:
    print("Submit method NOT found")

with open(path, 'w') as f:
    f.write(content)

print("Done")