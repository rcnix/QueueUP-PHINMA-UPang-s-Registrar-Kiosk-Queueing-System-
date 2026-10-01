from contextlib import contextmanager
import os
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import connection as PostgreSQLConnection


def _load_environment() -> None:
	project_root = Path(__file__).resolve().parents[1]
	project_env = project_root / ".env"
	source_env = project_root.parent / "FINAL" / ".env"
	load_dotenv(project_env if project_env.is_file() else source_env)


@contextmanager
def get_connection() -> Iterator[PostgreSQLConnection]:
	_load_environment()
	required = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST")
	missing = [name for name in required if not os.getenv(name)]
	if missing:
		raise psycopg2.OperationalError(
			"Missing PostgreSQL settings: " + ", ".join(missing)
		)

	try:
		port = int(os.getenv("DB_PORT", "5432"))
	except ValueError as error:
		raise psycopg2.OperationalError("DB_PORT must be an integer") from error

	connection = psycopg2.connect(
		dbname=os.environ["DB_NAME"],
		user=os.environ["DB_USER"],
		password=os.environ["DB_PASSWORD"],
		host=os.environ["DB_HOST"],
		port=port,
	)
	try:
		yield connection
		connection.commit()
	except Exception:
		connection.rollback()
		raise
	finally:
		connection.close()


def hash_password(password: str) -> str:
	import hashlib
	import secrets

	salt = secrets.token_bytes(16)
	digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
	return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
	import hashlib
	import hmac

	try:
		algorithm, iterations, salt_hex, expected_hex = encoded_hash.split("$")
		if algorithm != "pbkdf2_sha256":
			return False
		actual = hashlib.pbkdf2_hmac(
			"sha256",
			password.encode(),
			bytes.fromhex(salt_hex),
			int(iterations),
		)
		return hmac.compare_digest(actual.hex(), expected_hex)
	except (ValueError, TypeError):
		return False
