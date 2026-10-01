import tkinter.messagebox as messagebox

import psycopg2

from database.queries import issue_ticket
from printer.receipt_printer import print_receipt


class TicketWorkflowMixin:
	def _issue_ticket(self) -> None:
		concern_id = self.concern_ids.get(self.concern_choice.get())
		recipient_name = self.recipient_name.get().strip()
		if not recipient_name:
			messagebox.showwarning("Recipient required", "Enter the recipient name first.", parent=self)
			return
		if concern_id is None:
			messagebox.showwarning("No service", "There is no active concern for this counter.", parent=self)
			return
		try:
			ticket_number, counter_number, concern_name = issue_ticket(concern_id, recipient_name)
		except (psycopg2.Error, ValueError) as error:
			messagebox.showerror("Ticket error", str(error), parent=self)
			return
		self.ticket_details = (ticket_number, concern_name, counter_number)
		self.ticket_label.configure(text=ticket_number)
		self.ticket_info.configure(
			text=f"{recipient_name}  |  {concern_name}  |  Proceed to COUNTER {counter_number}"
		)
		self.print_button.configure(state="disabled")
		self._show_page("ticket")
		self._print_ticket()

	def _print_ticket(self) -> None:
		if self.ticket_details is None:
			return
		try:
			print_receipt(*self.ticket_details)
			self.print_status.set("Receipt sent to the default printer.")
			self.print_button.configure(state="disabled")
			self.status.set("Ticket issued. Proceed to your assigned counter.")
		except Exception as error:
			self.print_status.set(f"Automatic print failed: {error}")
			self.print_button.configure(state="normal")
			self.status.set("Your ticket is ready. Use Retry Receipt Print if needed.")

	def _finish_queue(self) -> None:
		self.ticket_details = None
		self.recipient_name.set("")
		self.ticket_label.configure(text="--")
		self.ticket_info.configure(text="")
		self.print_status.set("")
		self.status.set("Welcome. Start a queue.")
		self._show_page("home")