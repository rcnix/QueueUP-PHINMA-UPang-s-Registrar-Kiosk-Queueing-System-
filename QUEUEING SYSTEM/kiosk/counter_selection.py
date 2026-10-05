import psycopg2

from assets import format_counter_label
from database.queries import get_counters, get_faqs


class CounterSelectionMixin:
	def _refresh_counters(self) -> None:
		try:
			counters = get_counters()
		except psycopg2.Error as error:
			self.status.set(f"Could not load counters: {error}")
			counters = []
		self.counter_numbers = {
			format_counter_label(number, name): number
			for number, name, _prefix, _username in counters
		}
		values = list(self.counter_numbers) or ["No counters available"]
		current = self.counter_choice.get()
		selected = current if current in self.counter_numbers else values[0]
		self.counter_choice.set(selected)
		self.counter_menu.configure(
			values=values,
			state="normal" if self.counter_numbers else "disabled",
		)
		if selected != current:
			self._refresh_counter_faq()
		if hasattr(self, "concern_menu"):
			self._update_concern_options()
		if not counters:
			self.status.set("No counters are registered yet. Ask an administrator to create one.")

	def _on_counter_choice_changed(self, _value: str) -> None:
		self._refresh_counter_faq()
		self._update_concern_options()

	def _refresh_counter_faq(self) -> None:
		if not hasattr(self, "counter_faq_list"):
			return
		counter_number = self.counter_numbers.get(self.counter_choice.get())
		if counter_number is None:
			self._render_faqs(self.counter_faq_list, [])
			return
		try:
			faqs = get_faqs(counter_number=counter_number)
		except psycopg2.Error as error:
			self.status.set(f"Could not load counter FAQs: {error}")
			return
		self._render_faqs(self.counter_faq_list, faqs)