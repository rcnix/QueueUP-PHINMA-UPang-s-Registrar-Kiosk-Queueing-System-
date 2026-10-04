import customtkinter as ctk
import psycopg2

from assets import center_window, set_window_icon
from database.queries import get_queue_snapshot


class DisplayWindow(ctk.CTk):
	COUNTER_COUNT = 6

	def __init__(self):
		super().__init__()
		self.title("QueueUP - Queue Display")
		set_window_icon(self)
		self.geometry("1280x720")
		self.minsize(800, 480)
		center_window(self)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.status = ctk.StringVar(value="Connecting to queue service...")
		self.now_serving = [ctk.StringVar(value="--") for _ in range(self.COUNTER_COUNT)]
		self.up_next = [ctk.StringVar(value="--") for _ in range(self.COUNTER_COUNT)]
		self._build_ui()
		self._refresh()

	def _build_ui(self) -> None:
		ctk.CTkLabel(
			self,
			text="QUEUEUP  /  NOW SERVING",
			font=ctk.CTkFont(size=26, weight="bold"),
		).grid(row=0, column=0, padx=30, pady=(24, 12))
		board = ctk.CTkFrame(self, fg_color="transparent")
		board.grid(row=1, column=0, padx=24, pady=8, sticky="nsew")
		for row in range(2):
			board.grid_rowconfigure(row, weight=1)
		for column in range(3):
			board.grid_columnconfigure(column, weight=1)
		for index in range(self.COUNTER_COUNT):
			panel = ctk.CTkFrame(board, border_width=1)
			panel.grid(
				row=index // 3,
				column=index % 3,
				padx=10,
				pady=10,
				sticky="nsew",
			)
			panel.grid_columnconfigure(0, weight=1)
			ctk.CTkLabel(
				panel,
				text=f"COUNTER {index + 1}",
				font=ctk.CTkFont(size=17, weight="bold"),
			).grid(row=0, column=0, padx=12, pady=(18, 10))
			ctk.CTkLabel(panel, text="NOW SERVING", font=ctk.CTkFont(size=12)).grid(
				row=1, column=0, padx=12, pady=(4, 0)
			)
			ctk.CTkLabel(
				panel,
				textvariable=self.now_serving[index],
				font=ctk.CTkFont(size=38, weight="bold"),
			).grid(row=2, column=0, padx=12, pady=(0, 10))
			ctk.CTkLabel(panel, text="UP NEXT", font=ctk.CTkFont(size=12)).grid(
				row=3, column=0, padx=12, pady=(4, 0)
			)
			ctk.CTkLabel(
				panel,
				textvariable=self.up_next[index],
				font=ctk.CTkFont(size=24, weight="bold"),
			).grid(row=4, column=0, padx=12, pady=(0, 18))
		ctk.CTkLabel(self, textvariable=self.status).grid(
			row=2, column=0, padx=20, pady=(6, 14)
		)

	def _refresh(self) -> None:
		try:
			snapshot = get_queue_snapshot()
			for counter_number in range(1, self.COUNTER_COUNT + 1):
				serving, waiting = snapshot[counter_number]
				self.now_serving[counter_number - 1].set(
					serving or "--"
				)
				self.up_next[counter_number - 1].set(waiting[0] if waiting else "--")
			self.status.set("Live queue status")
		except psycopg2.Error as error:
			self.status.set(f"Queue service unavailable: {error}")
		self.after(1500, self._refresh)


def main() -> None:
	DisplayWindow().mainloop()
