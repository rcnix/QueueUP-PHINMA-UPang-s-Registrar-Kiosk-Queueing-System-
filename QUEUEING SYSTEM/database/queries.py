import re
from datetime import date, datetime

import psycopg2

from database.connection import get_connection, hash_password, verify_password
from database.models import SCHEMA_STATEMENTS


def ensure_schema() -> None:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute("SELECT pg_advisory_xact_lock(810024617)")
			for statement in SCHEMA_STATEMENTS:
				cursor.execute(statement)


def add_user(username: str, password: str, role: str = "admin") -> None:
	if role not in {"admin", "counter"}:
		raise ValueError("Unsupported user role")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
				(username, hash_password(password), role),
			)


def admin_exists() -> bool:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute("SELECT EXISTS (SELECT 1 FROM users WHERE role = 'admin')")
			return cursor.fetchone()[0]


def create_first_admin(username: str, password: str) -> None:
	username = username.strip()
	if not username or not password:
		raise ValueError("Username and password are required")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute("SELECT pg_advisory_xact_lock(810024617)")
			cursor.execute("SELECT EXISTS (SELECT 1 FROM users WHERE role = 'admin')")
			if cursor.fetchone()[0]:
				raise ValueError("An admin account already exists")
			cursor.execute(
				"INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'admin')",
				(username, hash_password(password)),
			)


def authenticate(username: str, password: str, role: str = "admin") -> bool:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT password_hash FROM users WHERE username = %s AND role = %s",
				(username, role),
			)
			row = cursor.fetchone()
	return row is not None and verify_password(password, row[0])


def authenticate_application_user(
	username: str,
	password: str,
	role: str,
) -> tuple[str, int | None] | None:
	if role not in {"admin", "counter"}:
		raise ValueError("Unsupported user role")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT u.password_hash, u.role, c.counter_number
				FROM users AS u
				LEFT JOIN counters AS c
					ON c.user_id = u.id AND c.active = TRUE
				WHERE u.username = %s AND u.role = %s
				""",
				(username, role),
			)
			row = cursor.fetchone()
	if row is None or not verify_password(password, row[0]):
		return None
	if row[1] == "counter" and row[2] is None:
		return None
	return row[1], row[2]


def get_kiosk_login_username() -> str | None:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute("SELECT username FROM kiosk_credentials WHERE id = 1")
			row = cursor.fetchone()
	return row[0] if row is not None else None


def configure_kiosk_login(username: str, password: str) -> None:
	username = username.strip()
	if not username or not password:
		raise ValueError("Kiosk username and password are required")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				INSERT INTO kiosk_credentials (id, username, password_hash)
				VALUES (1, %s, %s)
				ON CONFLICT (id) DO UPDATE
				SET username = EXCLUDED.username,
					password_hash = EXCLUDED.password_hash
				""",
				(username, hash_password(password)),
			)


def authenticate_kiosk_user(username: str, password: str) -> bool:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT password_hash FROM kiosk_credentials WHERE id = 1 AND username = %s",
				(username.strip(),),
			)
			row = cursor.fetchone()
	if row is None:
		return False
	return verify_password(password, row[0])


def authenticate_admin_password(password: str) -> bool:
	if not password:
		return False
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute("SELECT password_hash FROM users WHERE role = 'admin'")
			rows = cursor.fetchall()
	return any(verify_password(password, row[0]) for row in rows)


def create_counter_account(
	name: str,
	prefix: str,
	username: str,
	password: str,
) -> int:
	name = name.strip()
	prefix = prefix.strip().upper()
	username = username.strip()
	if not name or not username or not password:
		raise ValueError("Counter name, username, and password are required")
	if not re.fullmatch(r"[A-Z0-9]{1,6}", prefix):
		raise ValueError("Prefix must be 1-6 letters or numbers")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'counter') RETURNING id",
				(username, hash_password(password)),
			)
			user_id = cursor.fetchone()[0]
			cursor.execute(
				"INSERT INTO counter_passwords (user_id, password) VALUES (%s, %s)",
				(user_id, password),
			)
			cursor.execute(
				"INSERT INTO counters (name, prefix, user_id) VALUES (%s, %s, %s) RETURNING counter_number",
				(name, prefix, user_id),
			)
			return cursor.fetchone()[0]


def get_counters(active_only: bool = True) -> list[tuple[int, str, str, str]]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT c.counter_number, c.name, c.prefix, u.username
				FROM counters AS c
				JOIN users AS u ON u.id = c.user_id
				WHERE (%s = FALSE OR c.active = TRUE)
				ORDER BY c.counter_number
				""",
				(active_only,),
			)
			return cursor.fetchall()


def get_counter_password_map() -> list[tuple[int, str, str, str | None]]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT c.counter_number, c.name, u.username, cp.password
				FROM counters AS c
				JOIN users AS u ON u.id = c.user_id
				LEFT JOIN counter_passwords AS cp ON cp.user_id = u.id
				ORDER BY c.counter_number
				"""
			)
			return cursor.fetchall()


def delete_counter_account(counter_number: int) -> bool:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT u.id
				FROM users AS u
				JOIN counters AS c ON c.user_id = u.id
				WHERE c.counter_number = %s AND u.role = 'counter'
				FOR UPDATE OF u, c
				""",
				(counter_number,),
			)
			row = cursor.fetchone()
			if row is None:
				return False
			cursor.execute(
				"UPDATE concerns SET active = FALSE WHERE counter_number = %s",
				(counter_number,),
			)
			cursor.execute("DELETE FROM users WHERE id = %s", (row[0],))
			return cursor.rowcount == 1


def delete_all_application_data() -> None:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"TRUNCATE TABLE users, counters, concerns, faqs, tickets, ticket_sequences, kiosk_credentials RESTART IDENTITY CASCADE"
			)


def delete_user(username: str, password: str) -> bool:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT password_hash, role FROM users WHERE username = %s",
				(username,),
			)
			row = cursor.fetchone()
			if row is None or not verify_password(password, row[0]):
				return False
			if row[1] == "admin":
				cursor.execute(
					"TRUNCATE TABLE users, counters, concerns, faqs, tickets, ticket_sequences, kiosk_credentials RESTART IDENTITY CASCADE"
				)
			else:
				cursor.execute("DELETE FROM users WHERE username = %s", (username,))
	return True


def add_concern(name: str, counter_number: int) -> None:
	name = name.strip()
	if not name:
		raise ValueError("Concern name is required")
	if counter_number < 1:
		raise ValueError("Choose a registered counter")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT EXISTS (SELECT 1 FROM counters WHERE counter_number = %s AND active = TRUE)",
				(counter_number,),
			)
			if not cursor.fetchone()[0]:
				raise ValueError("Choose a registered counter")
			cursor.execute(
				"INSERT INTO concerns (name, counter_number) VALUES (%s, %s)",
				(name, counter_number),
			)


def get_concerns(active_only: bool = False) -> list[tuple[int, str, str, int, bool]]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT concerns.id, concerns.name, counters.prefix,
					concerns.counter_number, concerns.active
				FROM concerns
				JOIN counters USING (counter_number)
				WHERE (%s = FALSE OR concerns.active = TRUE)
				ORDER BY concerns.counter_number, concerns.name
				""",
				(active_only,),
			)
			return cursor.fetchall()


def set_concern_active(concern_id: int, active: bool) -> None:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"UPDATE concerns SET active = %s WHERE id = %s",
				(active, concern_id),
			)


def delete_concern(concern_id: int) -> bool:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT id FROM concerns WHERE id = %s FOR UPDATE",
				(concern_id,),
			)
			if cursor.fetchone() is None:
				return True
			cursor.execute(
				"SELECT EXISTS (SELECT 1 FROM tickets WHERE concern_id = %s)",
				(concern_id,),
			)
			has_history = cursor.fetchone()[0]
			if has_history:
				cursor.execute(
					"UPDATE concerns SET active = FALSE WHERE id = %s",
					(concern_id,),
				)
				return False
			cursor.execute("DELETE FROM concerns WHERE id = %s", (concern_id,))
			return cursor.rowcount > 0


def get_concern_stats() -> list[tuple[str, int, int]]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT c.name, c.counter_number, COUNT(t.id)::INTEGER
				FROM concerns AS c
			LEFT JOIN tickets AS t ON t.concern_id = c.id
			WHERE c.active = TRUE
			GROUP BY c.id, c.name, c.counter_number
			ORDER BY COUNT(t.id) DESC, c.name
			"""
			)
			return cursor.fetchall()


def get_faqs(
	counter_number: int | None = None,
	concern_id: int | None = None,
) -> list[tuple[int, str, str]]:
	if (counter_number is None) == (concern_id is None):
		raise ValueError("Choose exactly one FAQ target: counter or concern")
	if counter_number is not None:
		if counter_number < 1:
			raise ValueError("counter_number must be positive")
		where_clause = "counter_number = %s"
		parameter = counter_number
	else:
		where_clause = "concern_id = %s"
		parameter = concern_id
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				f"SELECT id, question, answer FROM faqs WHERE {where_clause} ORDER BY id",
				(parameter,),
			)
			return cursor.fetchall()


def save_faq(
	faq_id: int | None,
	question: str,
	answer: str,
	counter_number: int | None = None,
	concern_id: int | None = None,
) -> int:
	question = question.strip()
	answer = answer.strip()
	if not question or not answer:
		raise ValueError("Both the FAQ question and answer are required")
	if (counter_number is None) == (concern_id is None):
		raise ValueError("Choose exactly one FAQ target: counter or concern")
	if counter_number is not None and counter_number < 1:
		raise ValueError("counter_number must be positive")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			if faq_id is None:
				cursor.execute(
					"""
					INSERT INTO faqs (counter_number, concern_id, question, answer)
					VALUES (%s, %s, %s, %s) RETURNING id
					""",
					(counter_number, concern_id, question, answer),
				)
				return cursor.fetchone()[0]
			cursor.execute(
				"""
				UPDATE faqs
				SET counter_number = %s, concern_id = %s, question = %s, answer = %s
				WHERE id = %s
				""",
				(counter_number, concern_id, question, answer, faq_id),
			)
			if cursor.rowcount == 0:
				raise ValueError("That FAQ no longer exists")
			return faq_id


def delete_faq(faq_id: int) -> bool:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute("DELETE FROM faqs WHERE id = %s", (faq_id,))
			return cursor.rowcount > 0


def issue_ticket(
	concern_id: int,
	recipient_name: str | None = None,
) -> tuple[str, int, str]:
	recipient_name = recipient_name.strip() if recipient_name else None
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT counters.prefix, concerns.counter_number, concerns.name
				FROM concerns
			JOIN counters USING (counter_number)
			WHERE concerns.id = %s AND concerns.active = TRUE AND counters.active = TRUE
			FOR SHARE OF concerns, counters
				""",
				(concern_id,),
			)
			concern = cursor.fetchone()
			if concern is None:
				raise ValueError("That concern is unavailable")

			prefix, counter_number, concern_name = concern
			cursor.execute(
				"""
				INSERT INTO ticket_sequences (prefix, last_number)
				SELECT %s, COALESCE(
					MAX(substring(ticket_number FROM '[0-9]+$')::INTEGER), 0
				)
				FROM tickets
				WHERE left(ticket_number, length(%s) + 1) = %s || '-'
					AND ticket_number ~ ('^' || %s || '-[0-9]+$')
				ON CONFLICT (prefix) DO NOTHING
				""",
				(prefix, prefix, prefix, prefix),
			)
			cursor.execute(
				"UPDATE ticket_sequences SET last_number = last_number + 1 WHERE prefix = %s RETURNING last_number",
				(prefix,),
			)
			next_number = cursor.fetchone()[0]
			ticket_number = f"{prefix}-{next_number:03d}"
			cursor.execute(
				"""
				INSERT INTO tickets (ticket_number, counter_number, concern_id, recipient_name)
				VALUES (%s, %s, %s, %s)
				""",
				(ticket_number, counter_number, concern_id, recipient_name),
			)
	return ticket_number, counter_number, concern_name


def add_ticket(ticket_number: str, counter_number: int) -> None:
	if counter_number < 1:
		raise ValueError("counter_number must be positive")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				INSERT INTO tickets (ticket_number, counter_number)
				VALUES (%s, %s)
				""",
				(ticket_number, counter_number),
			)


def get_waiting_tickets(counter_number: int) -> list[str]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT ticket_number
				FROM tickets
				WHERE counter_number = %s AND status = 'waiting'
				ORDER BY id
				""",
				(counter_number,),
			)
			return [row[0] for row in cursor.fetchall()]


def get_serving_tickets() -> list[tuple[int, str]]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT counter_number, ticket_number FROM tickets WHERE status = 'serving' ORDER BY counter_number"
			)
			return cursor.fetchall()


def get_queue_snapshot() -> dict[int, tuple[str | None, list[str]]]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT counters.counter_number,
					active_ticket.ticket_number,
					COALESCE(waiting_tickets.ticket_numbers, ARRAY[]::TEXT[])
				FROM counters
				LEFT JOIN LATERAL (
					SELECT ticket_number
					FROM tickets
					WHERE counter_number = counters.counter_number AND status = 'serving'
					ORDER BY called_at DESC NULLS LAST, id DESC
					LIMIT 1
				) AS active_ticket ON TRUE
				LEFT JOIN LATERAL (
					SELECT array_agg(ticket_number ORDER BY id) AS ticket_numbers
					FROM tickets
					WHERE counter_number = counters.counter_number AND status = 'waiting'
				) AS waiting_tickets ON TRUE
				ORDER BY counters.counter_number
				"""
			)
			return {
				counter_number: (serving_ticket, waiting)
				for counter_number, serving_ticket, waiting in cursor.fetchall()
			}


def get_latest_tickets() -> dict[int, str | None]:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT counters.counter_number, latest.ticket_number
				FROM counters
				LEFT JOIN LATERAL (
					SELECT ticket_number
					FROM tickets
					WHERE tickets.counter_number = counters.counter_number
					ORDER BY id DESC
					LIMIT 1
				) AS latest ON TRUE
				ORDER BY counters.counter_number
				"""
			)
			return dict(cursor.fetchall())


def serve_next(counter_number: int) -> str | None:
	if counter_number < 1:
		raise ValueError("counter_number must be positive")
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT EXISTS (SELECT 1 FROM counters WHERE counter_number = %s AND active = TRUE)",
				(counter_number,),
			)
			if not cursor.fetchone()[0]:
				raise ValueError("That counter is not registered")
			cursor.execute(
				"""
				SELECT id, ticket_number
				FROM tickets
				WHERE counter_number = %s AND status = 'waiting'
				ORDER BY id
				LIMIT 1
				FOR UPDATE SKIP LOCKED
				""",
				(counter_number,),
			)
			row = cursor.fetchone()
			if row is None:
				cursor.execute(
					"""
					UPDATE tickets
					SET status = 'completed', completed_at = CURRENT_TIMESTAMP
					WHERE counter_number = %s AND status = 'serving'
						AND NOT EXISTS (
							SELECT 1 FROM tickets AS waiting
							WHERE waiting.counter_number = %s AND waiting.status = 'waiting'
						)
					""",
					(counter_number, counter_number),
				)
				return None
			cursor.execute(
				"""
				UPDATE tickets
				SET status = 'completed', completed_at = CURRENT_TIMESTAMP
				WHERE counter_number = %s AND status = 'serving'
				""",
				(counter_number,),
			)
			cursor.execute(
				"""
				UPDATE tickets
				SET status = 'serving', called_at = CURRENT_TIMESTAMP
				WHERE id = %s
				""",
				(row[0],),
			)
	return row[1]


def get_transactions(
	start_date: date | None = None,
	end_date: date | None = None,
	limit: int | None = 300,
	counter_number: int | None = None,
	search_text: str | None = None,
	ticket_number: str | None = None,
	status: str | None = None,
	concern_id: int | None = None,
) -> list[tuple[str, str | None, int, str, str | None, datetime, datetime | None, datetime | None]]:
	conditions = []
	parameters: list[object] = []
	if start_date is not None:
		conditions.append("t.created_at >= %s")
		parameters.append(start_date)
	if end_date is not None:
		conditions.append("t.created_at < %s")
		parameters.append(end_date)
	if counter_number is not None:
		if counter_number < 1:
			raise ValueError("counter_number must be positive")
		conditions.append("t.counter_number = %s")
		parameters.append(counter_number)
	if search_text and search_text.strip():
		conditions.append("t.recipient_name ILIKE %s")
		parameters.append(f"%{search_text.strip()}%")
	if ticket_number and ticket_number.strip():
		conditions.append("t.ticket_number ILIKE %s")
		parameters.append(f"%{ticket_number.strip()}%")
	if status is not None:
		if status not in {"waiting", "serving", "completed", "cancelled"}:
			raise ValueError("Unsupported ticket status")
		conditions.append("t.status = %s")
		parameters.append(status)
	if concern_id is not None:
		conditions.append("t.concern_id = %s")
		parameters.append(concern_id)
	where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
	limit_clause = ""
	if limit is not None:
		limit_clause = " LIMIT %s"
		parameters.append(max(1, min(limit, 5000)))
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				f"""
				SELECT t.ticket_number, c.name, t.counter_number, t.status,
					t.recipient_name,
					t.created_at, t.called_at, t.completed_at
				FROM tickets AS t
				LEFT JOIN concerns AS c ON c.id = t.concern_id
				{where_clause}
				ORDER BY t.created_at DESC, t.id DESC
				{limit_clause}
				""",
				tuple(parameters),
			)
			return cursor.fetchall()


def get_monthly_ticket_counts(
	year: int,
	month: int,
	counter_number: int | None = None,
) -> dict[date, int]:
	first_day = date(year, month, 1)
	next_month = date(year + (month == 12), month % 12 + 1, 1)
	conditions = ["created_at >= %s", "created_at < %s"]
	parameters: list[object] = [first_day, next_month]
	if counter_number is not None:
		if not 1 <= counter_number <= 6:
			raise ValueError("counter_number must be between 1 and 6")
		conditions.append("counter_number = %s")
		parameters.append(counter_number)
	with get_connection() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				f"""
				SELECT created_at::DATE, COUNT(*)::INTEGER
				FROM tickets
				WHERE {" AND ".join(conditions)}
				GROUP BY created_at::DATE
				ORDER BY created_at::DATE
				""",
				tuple(parameters),
			)
			return dict(cursor.fetchall())


def get_daily_transactions(
	target_date: date,
	counter_number: int | None = None,
) -> list[tuple[str, str | None, int, str, str | None, datetime, datetime | None, datetime | None]]:
	return get_transactions(
		target_date,
		date.fromordinal(target_date.toordinal() + 1),
		None,
		counter_number=counter_number,
	)


def cancel_waiting_tickets(counter_number: int | None = None) -> int:
	with get_connection() as connection:
		with connection.cursor() as cursor:
			if counter_number is None:
				cursor.execute(
					"""
					UPDATE tickets
					SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
					WHERE status = 'waiting'
					"""
				)
			else:
				cursor.execute(
					"""
					UPDATE tickets
					SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
					WHERE status = 'waiting' AND counter_number = %s
					""",
					(counter_number,),
				)
			return cursor.rowcount


def clear_queue() -> None:
	"""Preserve the legacy API without deleting transaction history."""
	cancel_waiting_tickets()
