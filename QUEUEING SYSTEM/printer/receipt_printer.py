"""Windows receipt printer for QueueUP ticket issuance.

Prints ticket receipts to the default printer using the Windows
win32print API. The receipt includes ticket details, concern name,
counter information, and the issue timestamp.
"""

from datetime import datetime
import platform

from assets import format_counter_label


# def print_receipt() - Prints a ticket receipt to the default Windows printer.
# Format:
# 	QUEUEUP
# 	-----------------------------------------
# 	Ticket: {ticket_number}
# 	Concern: {concern_name}
# 	Proceed to {counter} - {counter_name}
# 	Issued: {YYYY-MM-DD HH:MM}
# 	-----------------------------------------
# 	THANK YOU!
#
# Raises RuntimeError if not on Windows or if pywin32 is not installed.
def print_receipt(
	ticket_number: str,
	concern_name: str,
	counter_number: int,
	counter_name: str,
) -> None:
	if platform.system() != "Windows":
		raise RuntimeError("Receipt printing is currently configured for Windows.")

	try:
		import win32print
	except ImportError as error:
		raise RuntimeError(
			"Install the Windows printer support package with: pip install pywin32"
		) from error

	printer_name = win32print.GetDefaultPrinter()
	printer = win32print.OpenPrinter(printer_name)
	document_started = False
	page_started = False
	try:
		win32print.StartDocPrinter(printer, 1, ("QueueUP ticket", None, "RAW"))
		document_started = True
		win32print.StartPagePrinter(printer)
		page_started = True
		receipt = (
			"\x1b@"
			"\x1b"
			"QUEUEUP"
			"\n"
			"-----------------------------------------"
			"\n"
			f"Ticket: {ticket_number}"
			"\n"
			f"Concern: {concern_name}"
			"\n"
			f"Proceed to {format_counter_label(counter_number, counter_name)}"
			"\n"
			f"Issued: {datetime.now():%Y-%m-%d %H:%M}"
			"\n"
			"-----------------------------------------"
			"\n\n\n"
			"\x1d"
			"THANK YOU!"
			"\n"
		)
		win32print.WritePrinter(printer, receipt.encode("cp437", errors="replace"))
		win32print.EndPagePrinter(printer)
		page_started = False
		win32print.EndDocPrinter(printer)
		document_started = False
	except Exception:
		if page_started:
			win32print.EndPagePrinter(printer)
		if document_started:
			win32print.AbortPrinter(printer)
		raise
	finally:
		if page_started:
			win32print.EndPagePrinter(printer)
		if document_started:
			win32print.AbortPrinter(printer)
		win32print.ClosePrinter(printer)
