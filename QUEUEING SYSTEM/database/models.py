from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Ticket:
	id: int
	ticket_number: str
	counter_number: int
	status: str
	created_at: datetime
	concern_name: str | None = None


@dataclass(frozen=True)
class Concern:
	id: int
	name: str
	prefix: str
	counter_number: int
	active: bool


SCHEMA_STATEMENTS = (
	"""
	CREATE TABLE IF NOT EXISTS users (
		id BIGSERIAL PRIMARY KEY,
		username TEXT NOT NULL UNIQUE,
		password_hash TEXT NOT NULL,
		role TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'counter')),
		created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
	)
	""",
	"ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'admin'",
	"ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check",
	"ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'counter'))",
	"CREATE UNIQUE INDEX IF NOT EXISTS users_single_admin ON users (role) WHERE role = 'admin'",
	"""
	CREATE TABLE IF NOT EXISTS kiosk_credentials (
		id SMALLINT PRIMARY KEY CHECK (id = 1),
		username TEXT NOT NULL UNIQUE,
		password_hash TEXT NOT NULL
	)
	""",
	"""
	CREATE TABLE IF NOT EXISTS counter_passwords (
		user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
		password TEXT NOT NULL
	)
	""",
	"""
	CREATE TABLE IF NOT EXISTS counters (
		counter_number BIGSERIAL PRIMARY KEY,
		name TEXT NOT NULL UNIQUE,
		prefix TEXT NOT NULL UNIQUE CHECK (prefix ~ '^[A-Z0-9]{1,6}$'),
		user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
		active BOOLEAN NOT NULL DEFAULT TRUE,
		created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
	)
	""",
	"""
	CREATE TABLE IF NOT EXISTS concerns (
		id BIGSERIAL PRIMARY KEY,
		name TEXT NOT NULL UNIQUE,
		counter_number INTEGER NOT NULL CHECK (counter_number > 0),
		active BOOLEAN NOT NULL DEFAULT TRUE,
		created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
	)
	""",
	"ALTER TABLE concerns DROP CONSTRAINT IF EXISTS concerns_name_key",
	"ALTER TABLE concerns DROP CONSTRAINT IF EXISTS concerns_prefix_key",
	"ALTER TABLE concerns DROP COLUMN IF EXISTS prefix",
	"ALTER TABLE concerns DROP CONSTRAINT IF EXISTS concerns_counter_number_check",
	"ALTER TABLE concerns ADD CONSTRAINT concerns_counter_number_check CHECK (counter_number > 0)",
	"CREATE UNIQUE INDEX IF NOT EXISTS concerns_active_name_unique ON concerns (name) WHERE active = TRUE",
	"DROP INDEX IF EXISTS concerns_active_prefix_unique",
	"""
	CREATE TABLE IF NOT EXISTS faqs (
		id BIGSERIAL PRIMARY KEY,
		counter_number INTEGER CHECK (counter_number > 0),
		concern_id BIGINT REFERENCES concerns(id) ON DELETE CASCADE,
		question TEXT NOT NULL CHECK (length(trim(question)) > 0),
		answer TEXT NOT NULL CHECK (length(trim(answer)) > 0),
		CHECK ((counter_number IS NOT NULL) <> (concern_id IS NOT NULL))
	)
	""",
	"ALTER TABLE faqs DROP CONSTRAINT IF EXISTS faqs_counter_number_check",
	"ALTER TABLE faqs ADD CONSTRAINT faqs_counter_number_check CHECK (counter_number IS NULL OR counter_number > 0)",
	"CREATE INDEX IF NOT EXISTS faqs_by_concern ON faqs (concern_id, id)",
	"CREATE INDEX IF NOT EXISTS faqs_by_counter ON faqs (counter_number, id)",
	"""
	CREATE TABLE IF NOT EXISTS tickets (
		id BIGSERIAL PRIMARY KEY,
		ticket_number TEXT NOT NULL,
		counter_number INTEGER NOT NULL CHECK (counter_number > 0),
		status TEXT NOT NULL DEFAULT 'waiting'
			CHECK (status IN ('waiting', 'serving', 'completed', 'cancelled')),
		concern_id BIGINT REFERENCES concerns(id),
		recipient_name TEXT,
		created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
		called_at TIMESTAMPTZ,
		completed_at TIMESTAMPTZ
	)
	""",
	"ALTER TABLE tickets DROP CONSTRAINT IF EXISTS tickets_counter_number_check",
	"ALTER TABLE tickets ADD CONSTRAINT tickets_counter_number_check CHECK (counter_number > 0)",
	"""
	CREATE TABLE IF NOT EXISTS ticket_sequences (
		prefix TEXT PRIMARY KEY,
		last_number INTEGER NOT NULL CHECK (last_number >= 0)
	)
	""",
	"ALTER TABLE tickets ADD COLUMN IF NOT EXISTS concern_id BIGINT REFERENCES concerns(id)",
	"ALTER TABLE tickets ADD COLUMN IF NOT EXISTS recipient_name TEXT",
	"ALTER TABLE tickets ADD COLUMN IF NOT EXISTS called_at TIMESTAMPTZ",
	"ALTER TABLE tickets ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ",
	"ALTER TABLE tickets DROP CONSTRAINT IF EXISTS tickets_status_check",
	"""
	ALTER TABLE tickets ADD CONSTRAINT tickets_status_check
	CHECK (status IN ('waiting', 'serving', 'completed', 'cancelled'))
	""",
	"""
	CREATE INDEX IF NOT EXISTS tickets_waiting_by_counter
	ON tickets (counter_number, id) WHERE status = 'waiting'
	""",
	"""
	CREATE INDEX IF NOT EXISTS tickets_history_by_created_at
	ON tickets (created_at DESC)
	""",
	"""
	CREATE INDEX IF NOT EXISTS tickets_by_concern
	ON tickets (concern_id, created_at DESC)
	""",
)
