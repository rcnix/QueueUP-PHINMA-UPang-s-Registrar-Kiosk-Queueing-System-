path = r'c:/Users/bombie/OneDrive/Documents/PROJECT/QUEUEING SYSTEM/application.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find the registration window password entry block
# Look for the specific placeholder text to identify the right block
reg_start = None
reg_end = None
for i, line in enumerate(lines):
    if 'placeholder_text="Password (8+ characters)"' in line:
        reg_start = i
        break

if reg_start is not None:
    # Find the grid line after this entry
    for i in range(reg_start, min(reg_start + 15, len(lines))):
        if '.grid(row=5, column=0' in lines[i]:
            reg_end = i
            break
    print(f"Registration password block: lines {reg_start+1}-{reg_end+1}")
else:
    print("Registration password block NOT found")

# Find the confirm entry block  
conf_start = None
conf_end = None
for i, line in enumerate(lines):
    if 'placeholder_text="Confirm password"' in line:
        conf_start = i
        break

if conf_start is not None:
    for i in range(conf_start, min(conf_start + 15, len(lines))):
        if '.grid(row=8, column=0' in lines[i]:
            conf_end = i
            break
    print(f"Registration confirm block: lines {conf_start+1}-{conf_end+1}")
else:
    print("Registration confirm block NOT found")

# Find _submit method
submit_idx = None
for i, line in enumerate(lines):
    if 'def _submit(self) -> None:' in line:
        submit_idx = i
        break
print(f"_submit at line: {submit_idx+1}")

# Build new lines
new_lines = []

# Copy everything up to (but not including) the entry creation line
new_lines.extend(lines[:reg_start-2])

# Add new password entry block
new_lines.append('\t\tself.password_entry = ctk.CTkEntry(\n')
new_lines.append('\t\t\tpanel,\n')
new_lines.append('\t\t\tplaceholder_text="Password (8+ characters)",\n')
new_lines.append('\t\t\tshow="*",\n')
new_lines.append('\t\t\twidth=320,\n')
new_lines.append('\t\t\tfont=ctk.CTkFont(family="Bahnschrift", size=13),\n')
new_lines.append('\t\t)\n')
new_lines.append('\t\tself.password_frame = ctk.CTkFrame(panel, fg_color="transparent")\n')
new_lines.append('\t\tself.password_frame.grid(row=5, column=0, padx=16, pady=4, sticky="ew")\n')
new_lines.append('\t\tself.password_frame.grid_columnconfigure(0, weight=1)\n')
new_lines.append('\t\tself.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))\n')
new_lines.append('\t\tself._show_password = False\n')
new_lines.append('\t\tself.show_password_btn = ctk.CTkButton(\n')
new_lines.append('\t\t\tself.password_frame,\n')
new_lines.append('\t\t\ttext="\u2605",\n')
new_lines.append('\t\t\twidth=30,\n')
new_lines.append('\t\t\tcommand=self._toggle_password_visibility,\n')
new_lines.append('\t\t\tfont=ctk.CTkFont(family="Bahnschrift", size=13),\n')
new_lines.append('\t\t)\n')
new_lines.append('\t\tself.show_password_btn.grid(row=0, column=1)\n')

# Skip the old block (reg_start to reg_end inclusive), continue after it
new_lines.extend(lines[reg_end+1:conf_start])

# Add new confirm entry block
new_lines.append('\t\tself.confirm_entry = ctk.CTkEntry(\n')
new_lines.append('\t\t\tpanel,\n')
new_lines.append('\t\t\tplaceholder_text="Confirm password",\n')
new_lines.append('\t\t\tshow="*",\n')
new_lines.append('\t\t\twidth=320,\n')
new_lines.append('\t\t\tfont=ctk.CTkFont(family="Bahnschrift", size=13),\n')
new_lines.append('\t\t)\n')
new_lines.append('\t\tself.confirm_frame = ctk.CTkFrame(panel, fg_color="transparent")\n')
new_lines.append('\t\tself.confirm_frame.grid(row=8, column=0, padx=16, pady=2, sticky="ew")\n')
new_lines.append('\t\tself.confirm_frame.grid_columnconfigure(0, weight=1)\n')
new_lines.append('\t\tself.confirm_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))\n')
new_lines.append('\t\tself._show_confirm = False\n')
new_lines.append('\t\tself.show_confirm_btn = ctk.CTkButton(\n')
new_lines.append('\t\t\tself.confirm_frame,\n')
new_lines.append('\t\t\ttext="\u2605",\n')
new_lines.append('\t\t\twidth=30,\n')
new_lines.append('\t\t\tcommand=self._toggle_confirm_visibility,\n')
new_lines.append('\t\t\tfont=ctk.CTkFont(family="Bahnschrift", size=13),\n')
new_lines.append('\t\t)\n')
new_lines.append('\t\tself.show_confirm_btn.grid(row=0, column=1)\n')

# Skip old confirm block, continue after it
new_lines.extend(lines[conf_end+1:submit_idx])

# Add toggle methods before _submit
new_lines.append('\n')
new_lines.append('\tdef _toggle_password_visibility(self) -> None:\n')
new_lines.append('\t\tself._show_password = not self._show_password\n')
new_lines.append('\t\tself.password_entry.configure(show="" if self._show_password else "*")\n')
new_lines.append('\t\tself.show_password_btn.configure(text="\u2605" if self._show_password else "\u2606")\n')
new_lines.append('\n')
new_lines.append('\tdef _toggle_confirm_visibility(self) -> None:\n')
new_lines.append('\t\tself._show_confirm = not self._show_confirm\n')
new_lines.append('\t\tself.confirm_entry.configure(show="" if self._show_confirm else "*")\n')
new_lines.append('\t\tself.show_confirm_btn.configure(text="\u2605" if self._show_confirm else "\u2606")\n')
new_lines.append('\n')

# Add the rest from _submit onwards
new_lines.extend(lines[submit_idx:])

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Done. New total lines: {len(new_lines)}")