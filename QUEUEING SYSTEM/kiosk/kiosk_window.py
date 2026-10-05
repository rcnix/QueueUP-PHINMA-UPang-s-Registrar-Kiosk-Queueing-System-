import sys
from pathlib import Path

import customtkinter as ctk

if __package__ in (None, ""):
	sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assets import center_window, set_window_icon
from kiosk.concern_selection import ConcernSelectionMixin
from kiosk.counter_selection import CounterSelectionMixin
from kiosk.ticket import TicketWorkflowMixin


FONT_FAMILY = "Bahnschrift"
GREEN = "#397A45"
GREEN_HOVER = "#2F6639"
PALE_GREEN = "#E8F3E8"
INK = "#183B22"
FAQ_MUTED = "#7B887D"


class KioskWindow(
	CounterSelectionMixin,
	ConcernSelectionMixin,
	TicketWorkflowMixin,
	ctk.CTkFrame,
):
	COUNTER_COUNT = 6

	def __init__(self, parent):
		super().__init__(parent, corner_radius=0, fg_color=PALE_GREEN)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.concern_ids: dict[str, int] = {}
		self.concern_counters: dict[str, int] = {}
		self.ticket_details: tuple[str, str, int] | None = None
		self.counter_choice = ctk.StringVar(value="No counters available")
		self.counter_numbers: dict[str, int] = {}
		self.concern_choice = ctk.StringVar(value="Choose a concern")
		self.status = ctk.StringVar(value="Welcome. Start a queue.")
		self.print_status = ctk.StringVar(value="")
		self.recipient_name = ctk.StringVar(value="")
		self._build_ui()
		self._refresh_concerns()
		self._refresh_counter_faq()

	def _build_ui(self) -> None:
		header = ctk.CTkFrame(self, fg_color="transparent")
		header.grid(row=0, column=0, padx=28, pady=(20, 10), sticky="ew")
		header.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			header,
			text="QueueUP",
			font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
			text_color=INK,
			anchor="w",
		).grid(row=0, column=0, sticky="w")
		ctk.CTkLabel(
			header,
			text="SERVICE QUEUE",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			text_color=GREEN,
			anchor="e",
		).grid(row=0, column=1, sticky="e")
		self.page_area = ctk.CTkFrame(
			self,
			fg_color="#F7FBF6",
			border_width=1,
			border_color="#BCD5BE",
			corner_radius=8,
		)
		self.page_area.grid(row=1, column=0, padx=18, pady=6, sticky="nsew")
		self.page_area.grid_columnconfigure(0, weight=1)
		self.page_area.grid_rowconfigure(0, weight=1)
		self.pages = {
			name: ctk.CTkScrollableFrame(
				self.page_area,
				fg_color="transparent",
				scrollbar_button_color=GREEN,
				scrollbar_button_hover_color=GREEN_HOVER,
			)
			for name in ("home", "counter", "concern", "ticket")
		}
		for page in self.pages.values():
			page.place(relx=0, rely=0, relwidth=1, relheight=1)
			page.place_forget()
		self._build_home_page()
		self._build_counter_page()
		self._build_concern_page()
		self._build_ticket_page()
		self._show_page("home")

	def _build_home_page(self) -> None:
		page = self.pages["home"]
		page.grid_columnconfigure(0, weight=1)
		ctk.CTkLabel(
			page,
			text="Welcome To QueueUP!",
			font=ctk.CTkFont(family=FONT_FAMILY, size=27, weight="bold"),
			text_color=INK,
		).pack(padx=24, pady=(42, 8))
		ctk.CTkLabel(
			page,
			text="Start Queueing! - Choose a counter and concern to take your place in line.",
			font=ctk.CTkFont(family=FONT_FAMILY, size=14),
			text_color="#52765A",
			wraplength=580,
			justify="center",
		).pack(padx=24, pady=(0, 30))
		self._action_button(page, "START QUEUE", self._start_queue, width=330).pack(pady=8)

	def _build_counter_page(self) -> None:
		page = self.pages["counter"]
		page.grid_columnconfigure(0, weight=1)
		self._page_heading(page, "Choose a Counter", "Pick the counter that handles your service.")
		ctk.CTkLabel(
			page,
			text="STEP 1 OF 2",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			text_color=GREEN,
		).pack(pady=(22, 8))
		self.counter_menu = ctk.CTkOptionMenu(
			page,
			variable=self.counter_choice,
			values=["No counters available"],
			command=self._on_counter_choice_changed,
			width=390,
			height=54,
			font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.counter_menu.pack(pady=10)
		self.counter_faq_list = self._build_faq_panel(page, "COUNTER FAQs")
		self._action_button(page, "CONTINUE", self._next_to_concern, width=290).pack(pady=12)
		self._build_page_navigation(
			page,
			back=lambda: self._show_page("home"),
		)

	def _build_concern_page(self) -> None:
		page = self.pages["concern"]
		page.grid_columnconfigure(0, weight=1)
		self._page_heading(page, "Choose your Concern", "Your concern tells the counter what service you need.")
		ctk.CTkLabel(
			page,
			text="STEP 2 OF 2",
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			text_color=GREEN,
		).pack(pady=(10, 5))
		self.concern_menu = ctk.CTkOptionMenu(
			page,
			variable=self.concern_choice,
			values=["Choose a concern"],
			command=lambda _value: self._refresh_concern_faq(),
			width=440,
			height=54,
			font=ctk.CTkFont(family=FONT_FAMILY, size=14),
			fg_color=GREEN,
			button_color=GREEN_HOVER,
			button_hover_color=INK,
		)
		self.concern_menu.pack(pady=(5, 12))
		ctk.CTkLabel(
			page,
			text="RECIPIENT NAME",
			font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
			text_color=INK,
		).pack(pady=(2, 5))
		self.recipient_entry = ctk.CTkEntry(
			page,
			textvariable=self.recipient_name,
			placeholder_text="Name for this ticket",
			width=440,
			height=50,
			font=ctk.CTkFont(family=FONT_FAMILY, size=14),
		)
		self.recipient_entry.pack(pady=(0, 14))
		self._action_button(page, "SUBMIT QUEUE", self._issue_ticket, width=320).pack(pady=8)
		self.concern_faq_list = self._build_faq_panel(page, "CONCERN FAQs")
		self.recipient_entry.bind("<Return>", lambda _event: self._issue_ticket())
		self._build_page_navigation(
			page,
			back=lambda: self._show_page("counter"),
		)

	def _build_ticket_page(self) -> None:
		page = self.pages["ticket"]
		page.grid_columnconfigure(0, weight=1)
		self._page_heading(page, "Thank you!", "Keep your ticket number and proceed to the assigned counter.")
		self.ticket_label = ctk.CTkLabel(
			page,
			text="--",
			font=ctk.CTkFont(family=FONT_FAMILY, size=56, weight="bold"),
			text_color=INK,
		)
		self.ticket_label.pack(pady=(30, 4))
		self.ticket_info = ctk.CTkLabel(
			page,
			text="",
			font=ctk.CTkFont(family=FONT_FAMILY, size=15),
			text_color=INK,
			wraplength=560,
			justify="center",
		)
		self.ticket_info.pack(padx=20, pady=4)
		ctk.CTkLabel(
			page,
			textvariable=self.print_status,
			font=ctk.CTkFont(family=FONT_FAMILY, size=12),
			text_color=GREEN,
			wraplength=560,
			justify="center",
		).pack(padx=20, pady=(8, 6))
		self.print_button = self._action_button(page, "RETRY RECEIPT PRINT", self._print_ticket, width=230)
		self.print_button.pack(pady=6)
		self._action_button(
			page,
			"DONE",
			self._finish_queue,
			width=180,
			secondary=True,
		).pack(pady=(10, 4))

	def _build_faq_panel(self, page, title: str):
		panel = ctk.CTkFrame(
			page,
			fg_color="#EDF4ED",
			border_width=1,
			border_color="#D5E2D6",
			corner_radius=6,
		)
		panel.pack(fill="x", padx=24, pady=(6, 4))
		ctk.CTkLabel(
			panel,
			text=title,
			font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
			text_color="#52765A",
		).pack(pady=(8, 2))
		faq_list = ctk.CTkScrollableFrame(
			panel,
			height=116,
			fg_color="transparent",
			corner_radius=0,
		)
		faq_list.pack(fill="x", padx=8, pady=(0, 6))
		return faq_list

	def _render_faqs(self, target, faqs) -> None:
		for child in target.winfo_children():
			child.destroy()
		if not faqs:
			ctk.CTkLabel(
				target,
				text="No FAQs for this counter yet.",
				font=ctk.CTkFont(family=FONT_FAMILY, size=13),
				text_color=FAQ_MUTED,
				justify="center",
				wraplength=700,
			).pack(fill="x", padx=8, pady=20)
			return
		for _faq_id, question, answer in faqs:
			ctk.CTkLabel(
				target,
				text=question,
				font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
				text_color="#52765A",
				justify="center",
				wraplength=700,
			).pack(fill="x", padx=8, pady=(8, 2))
			ctk.CTkLabel(
				target,
				text=answer,
				font=ctk.CTkFont(family=FONT_FAMILY, size=12),
				text_color=FAQ_MUTED,
				justify="center",
				wraplength=700,
			).pack(fill="x", padx=8, pady=(0, 8))

	def _page_heading(self, page, title: str, subtitle: str | None = None) -> None:
		ctk.CTkLabel(
			page,
			text=title,
			font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
			text_color=INK,
		).pack(padx=20, pady=(28, 4))
		if subtitle:
			ctk.CTkLabel(
				page,
				text=subtitle,
				font=ctk.CTkFont(family=FONT_FAMILY, size=13),
				text_color="#52765A",
				wraplength=600,
				justify="center",
			).pack(padx=20, pady=(0, 8))

	def _build_page_navigation(
		self,
		page,
		back,
	) -> None:
		bar = ctk.CTkFrame(page, fg_color="transparent")
		bar.pack(fill="x", padx=20, pady=(10, 12))
		bar.grid_columnconfigure(0, weight=1)
		bar.grid_columnconfigure(2, weight=1)
		self._action_button(bar, "BACK", back, width=150, secondary=True).grid(
			row=0, column=1
		)

	@staticmethod
	def _action_button(parent, text: str, command, width: int, secondary: bool = False):
		return ctk.CTkButton(
			parent,
			text=text,
			command=command,
			width=width,
			height=56,
			font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
			fg_color="#DDEBDD" if secondary else GREEN,
			hover_color="#C6DEC7" if secondary else GREEN_HOVER,
			text_color=INK if secondary else "white",
		)

	def _show_page(self, page_name: str) -> None:
		for page in self.pages.values():
			page.place_forget()
		self.pages[page_name].place(relx=0, rely=0, relwidth=1, relheight=1)
		self.pages[page_name].tkraise()

	def _start_queue(self) -> None:
		self._refresh_counter_faq()
		self.status.set("Choose the counter assigned to your service.")
		self._show_page("counter")

def main() -> None:
	root = ctk.CTk()
	root.title("QueueUP - Get a Ticket")
	root.geometry("980x900")
	root.minsize(800, 740)
	center_window(root)
	set_window_icon(root)
	KioskWindow(root).pack(fill="both", expand=True)
	root.mainloop()


if __name__ == "__main__":
	main()