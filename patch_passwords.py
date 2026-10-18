path = r'c:/Users/bombie/OneDrive/Documents/PROJECT/QUEUEING SYSTEM/application.py'

with open(path, 'r') as f:
    lines = f.readlines()

# Replace password entry block (lines 252-259, indices 251-258)
old_start = None
for i, line in enumerate(lines):
    if 'self.password_entry = ctk.CTkEntry(' in line:
        old_start = i
        break

if old_start is not None:
    # Find the end of the block (the grid line)
    old_end = None
    for i in range(old_start, min(old_start + 20, len(lines))):
        if '.grid(row=5, column=0' in lines[i]:
            old_end = i
            break
    
    if old_end is not None:
        new_block = '''		self.password_entry = ctk.CTkEntry(
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
		self.show_password_btn.grid(row=0, column=1)
'''
        lines[old_start:old_end+1] = [new_block]
        print(f'Replaced lines {old_start+1}-{old_end+1}')
    else:
        print('Could not find grid line for password entry')
else:
    print('Could not find password entry line')

# Replace confirm entry block  
old_start2 = None
for i, line in enumerate(lines):
    if 'self.confirm_entry = ctk.CTkEntry(' in line:
        old_start2 = i
        break

if old_start2 is not None:
    old_end2 = None
    for i in range(old_start2, min(old_start2 + 20, len(lines))):
        if '.grid(row=8, column=0' in lines[i]:
            old_end2 = i
            break
    
    if old_end2 is not None:
        new_block2 = '''		self.confirm_entry = ctk.CTkEntry(
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
		self.show_confirm_btn.grid(row=0, column=1)
'''
        lines[old_start2:old_end2+1] = [new_block2]
        print(f'Replaced lines {old_start2+1}-{old_end2+1}')
    else:
        print('Could not find grid line for confirm entry')
else:
    print('Could not find confirm entry line')

# Add toggle methods after _build_form method ends (before _submit)
# Find _submit method and insert toggle methods before it
submit_line = None
for i, line in enumerate(lines):
    if 'def _submit(self) -> None:' in line:
        submit_line = i
        break

if submit_line is not None:
    toggle_methods = '''

	def _toggle_password_visibility(self) -> None:
		self._show_password = not self._show_password
		self.password_entry.configure(show="" if self._show_password else "*")
		self.show_password_btn.configure(text="\u2605" if self._show_password else "\u2606")

	def _toggle_confirm_visibility(self) -> None:
		self._show_confirm = not self._show_confirm
		self.confirm_entry.configure(show="" if self._show_confirm else "*")
		self.show_confirm_btn.configure(text="\u2605" if self._show_confirm else "\u2606")

'''
    lines.insert(submit_line, toggle_methods)
    print(f'Inserted toggle methods before line {submit_line+1}')

with open(path, 'w') as f:
    f.writelines(lines)

print('Done patching')