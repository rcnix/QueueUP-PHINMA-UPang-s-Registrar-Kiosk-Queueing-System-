# EMAIL VERIFICATION - ADMIN UI
# Handles sending email verification codes to admin users for account
# creation, password recovery, and email address updates via SMTP.

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from dotenv import load_dotenv

from database.queries import issue_admin_email_code, revoke_admin_email_code


# def _load_mail_settings() -> tuple[str, int, str, str, str] - Loads SMTP
# configuration from environment files, searching project and parent FINAL
# directories as fallbacks.
def _load_mail_settings() -> tuple[str, int, str, str, str]:
	project_root = Path(__file__).resolve().parents[1]
	project_env = project_root / ".env"
	source_env = project_root.parent / "FINAL" / ".env"
	load_dotenv(project_env if project_env.is_file() else source_env)

	host = os.getenv("SMTP_HOST", "").strip()
	username = os.getenv("SMTP_USERNAME", "").strip()
	password = os.getenv("SMTP_PASSWORD", "")
	from_address = os.getenv("SMTP_FROM_EMAIL", "").strip()
	if not host or not username or not password or not from_address:
		raise ValueError(
			"Configure SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and "
			"SMTP_FROM_EMAIL in QUEUEING SYSTEM/.env"
		)
	try:
		port = int(os.getenv("SMTP_PORT", "587"))
	except ValueError as error:
		raise ValueError("SMTP_PORT must be a valid port number") from error
	if not 1 <= port <= 65535:
		raise ValueError("SMTP_PORT must be between 1 and 65535")
	return host, port, username, password, from_address


# def _send_code() - Sends a verification email with a temporary code to the
# specified recipient using the configured SMTP server.
def _send_code(email: str, code: str, purpose: str) -> None:
	host, port, username, password, from_address = _load_mail_settings()
	message = EmailMessage()
	message["Subject"] = {
		"signup": "Verify your QueueUP Admin Email",
		"recovery": "QueueUP Admin Account Recovery",
		"email_update": "Verify your QueueUP Recovery Email",
	}[purpose]
	message["From"] = formataddr(("QueueUp_no-reply", from_address))
	message["To"] = email
	message.set_content(
		f"Good day!\n\n"
		f"Your QueueUP verification code is {code}.\n\n"
		"This code expires in 5 minutes and can only be used once. "
		"If you did not request it, you can ignore this message."
	)
	context = ssl.create_default_context()
	if port == 465:
		with smtplib.SMTP_SSL(
			host, port, timeout=15, context=context
		) as server:
			server.login(username, password)
			server.send_message(message)
	else:
		with smtplib.SMTP(host, port, timeout=15) as server:
			server.ehlo()
			server.starttls(context=context)
			server.ehlo()
			server.login(username, password)
			server.send_message(message)


# def issue_and_send_admin_code() - Generates a verification code and sends
# it via email, returning True on success or False if no code was issued.
def issue_and_send_admin_code(
	email: str,
	purpose: str,
	current_password: str = "",
) -> bool:
	email = email.strip().casefold()
	code = issue_admin_email_code(email, purpose, current_password)
	if code is None:
		return False
	try:
		_send_code(email, code, purpose)
	except (OSError, smtplib.SMTPException, ValueError):
		revoke_admin_email_code(email, purpose)
		raise
	return True
