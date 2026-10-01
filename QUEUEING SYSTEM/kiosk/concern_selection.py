import tkinter.messagebox as messagebox

import psycopg2

from database.queries import get_concerns, get_faqs


class ConcernSelectionMixin:
	def _next_to_concern(self) -> None:
		self._update_concern_options()
		if not any(
			counter == int(self.counter_choice.get().replace("COUNTER ", ""))
			for counter in self.concern_counters.values()
		):
			messagebox.showwarning(
				"No services at this counter",
				"Choose a counter with an active concern.",
				parent=self,
			)
			return
		self._refresh_concern_faq()
		self.status.set("Choose the concern that matches your request.")
		self._show_page("concern")

	def _refresh_concerns(self) -> None:
		try:
			concerns = get_concerns(active_only=True)
			self.concern_ids = {
				f"{name} ({prefix})": concern_id
				for concern_id, name, prefix, _counter_number, _active in concerns
			}
			self.concern_counters = {
				f"{name} ({prefix})": counter_number
				for _concern_id, name, prefix, counter_number, _active in concerns
			}
			self._update_concern_options()
			if not concerns:
				self.status.set("No active services. Ask an administrator to add one.")
		except psycopg2.Error as error:
			self.status.set(f"Could not load services: {error}")
		if self.winfo_exists():
			self.after(2000, self._refresh_concerns)

	def _update_concern_options(self) -> None:
		if not hasattr(self, "concern_menu"):
			return
		counter_number = int(self.counter_choice.get().replace("COUNTER ", ""))
		choices = [
			name for name, assigned_counter in self.concern_counters.items()
			if assigned_counter == counter_number
		]
		if not choices:
			choices = ["No active concerns for this counter"]
		self.concern_menu.configure(values=choices)
		current = self.concern_choice.get()
		selected = current if current in choices else choices[0]
		self.concern_choice.set(selected)
		self.concern_menu.configure(
			state="normal" if choices[0] != "No active concerns for this counter" else "disabled"
		)
		if selected != current:
			self._refresh_concern_faq()

	def _refresh_concern_faq(self) -> None:
		if not hasattr(self, "concern_faq_list"):
			return
		concern_id = self.concern_ids.get(self.concern_choice.get())
		if concern_id is None:
			self._render_faqs(self.concern_faq_list, [])
			return
		try:
			faqs = get_faqs(concern_id=concern_id)
		except psycopg2.Error as error:
			self.status.set(f"Could not load concern FAQs: {error}")
			return
		self._render_faqs(self.concern_faq_list, faqs)