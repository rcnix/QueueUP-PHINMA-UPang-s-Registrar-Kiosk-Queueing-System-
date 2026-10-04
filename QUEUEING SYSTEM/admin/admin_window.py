import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from admin.dashboard import AdminDashboard
from admin.styles import FONT_FAMILY, GREEN, INK, PALE_GREEN
from assets import set_window_icon
from database.queries import ensure_schema, get_queue_snapshot




class MainFrame(ctk.CTkFrame):
	COUNTER_COUNT = 6

	def __init__(self, parent):
		super().__init__(parent, corner_radius=0, fg_color=PALE_GREEN)
		self.root = self.winfo_toplevel()
		self.pack(fill="both", expand=True)
		self.current_tickets = [
			tk.StringVar(value="--") for _ in range(self.COUNTER_COUNT)
		]
		self.status = tk.StringVar(value="Live counter activity is being updated in real time.")
		self._refresh_job = None
		self._build_dashboard()
		self._refresh_queues()

	def _build_dashboard(self) -> None:
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		header = ctk.CTkFrame(self, fg_color="transparent")
		header.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
		header.grid_columnconfigure(0, weight=1)
		header.grid_columnconfigure(1, weight=1)
		ctk.CTkLabel(
			header,
			text="LIVE COUNTER",
			font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
			text_color=INK,
			anchor="center",
		).grid(row=0, column=0, columnspan=2, sticky="ew")
		ctk.CTkLabel(
			header,
			text="Live Counter Display for QueueUP",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			text_color=GREEN,
			anchor="center",
		).grid(row=1, column=0, columnspan=2, pady=(2, 0), sticky="ew")

		counter_grid = ctk.CTkFrame(self, fg_color="transparent")
		counter_grid.grid(row=1, column=0, padx=16, pady=6, sticky="nsew")
		for row in range(2):
			counter_grid.grid_rowconfigure(row, weight=1, uniform="counter-row")
		for column in range(3):
			counter_grid.grid_columnconfigure(column, weight=1, uniform="counter-column")
		for index in range(self.COUNTER_COUNT):
			self._build_counter_panel(counter_grid, index)

		ctk.CTkLabel(
			self,
			textvariable=self.status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11),
			text_color=INK,
			anchor="center",
		).grid(row=2, column=0, padx=24, pady=(6, 16), sticky="ew")

	def _build_counter_panel(self, parent, index: int) -> None:
		panel = ctk.CTkFrame(
			parent,
			fg_color="#F7FBF6",
			border_width=1,
			border_color="#BCD5BE",
			corner_radius=8,
		)
		panel.grid(
			row=index // 3,
			column=index % 3,
			padx=10,
			pady=10,
			sticky="nsew",
		)
		panel.grid_columnconfigure(0, weight=1)
		panel.grid_rowconfigure(2, weight=1)
		ctk.CTkLabel(
			panel,
			text=f"COUNTER {index + 1}",
			font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
			text_color=GREEN,
		).grid(row=0, column=0, padx=12, pady=(16, 2))
		ctk.CTkLabel(
			panel,
			text="NOW SERVING",
			font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
			text_color="#52765A",
		).grid(row=1, column=0, padx=12, pady=(4, 0))
		ctk.CTkLabel(
			panel,
			textvariable=self.current_tickets[index],
			font=ctk.CTkFont(family=FONT_FAMILY, size=44, weight="bold"),
			text_color=INK,
		).grid(row=2, column=0, padx=12, pady=(0, 18), sticky="nsew")

	def _refresh_queues(self) -> None:
		try:
			snapshot = get_queue_snapshot()
			for counter_number, (serving, _waiting) in snapshot.items():
				self.current_tickets[counter_number - 1].set(serving or "--")
			self.status.set("Live counter activity is being updated in real time.")
		except psycopg2.Error as error:
			self.status.set(f"Could not refresh counters: {error}")
		if self.winfo_exists():
			self._refresh_job = self.after(2000, self._refresh_queues)

	def destroy(self) -> None:
		if self._refresh_job is not None:
			try:
				self.after_cancel(self._refresh_job)
			except tk.TclError:
				pass
		super().destroy()


def main(prepare_schema: bool = True) -> None:
	ctk.set_appearance_mode("Light")
	ctk.set_default_color_theme("green")
	ctk.ThemeManager.theme["CTkFont"]["family"] = FONT_FAMILY
	root = ctk.CTk()
	root.title("QueueUP Admin")
	root.geometry("1200x800")
	root.minsize(850, 560)
	set_window_icon(root)
	if prepare_schema:
		try:
			ensure_schema()
		except psycopg2.Error as error:
			messagebox.showerror(
				"Database setup error",
				"Could not prepare the PostgreSQL database.\n\n"
				f"{error}\n\n"
				"Check that PostgreSQL is running and that .env has the "
				"correct database, username, password, host, and port!",
				parent=root,
			)
			root.destroy()
			return
	AdminDashboard(root)
	root.mainloop()


if __name__ == "__main__":
	main()