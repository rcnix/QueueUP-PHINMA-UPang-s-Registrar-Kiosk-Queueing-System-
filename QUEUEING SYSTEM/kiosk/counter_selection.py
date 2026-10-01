import psycopg2

from database.queries import get_faqs


class CounterSelectionMixin:
	def _refresh_counter_faq(self) -> None:
		if not hasattr(self, "counter_faq_list"):
			return
		counter_number = int(self.counter_choice.get().replace("COUNTER ", ""))
		try:
			faqs = get_faqs(counter_number=counter_number)
		except psycopg2.Error as error:
			self.status.set(f"Could not load counter FAQs: {error}")
			return
		self._render_faqs(self.counter_faq_list, faqs)