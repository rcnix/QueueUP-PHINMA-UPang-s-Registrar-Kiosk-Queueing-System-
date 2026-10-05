from datetime import datetime
import platform


def print_receipt(ticket_number: str, concern_name: str, counter_number: int) -> None:
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
			"\x1b@\x1ba\x01"
			"QUEUEUP\n"
			"\x1ba\x00"
			"-----------------------------------------\n"
			f"Ticket: {ticket_number}\n"
			f"Concern: {concern_name}\n"
			f"Proceed to Counter {counter_number}\n"
			f"Issued: {datetime.now():%Y-%m-%d %H:%M}\n"
			"-----------------------------------------\n\n\n\x1dV\x00"
			"THANK YOU!\n"
		)
		win32print.WritePrinter(printer, receipt.encode("cp437", errors="replace"))
		win32print.EndPagePrinter(printer)
		page_started = False
		win32print.EndDocPrinter(printer)
		document_started = False
	finally:
		if page_started:
			win32print.EndPagePrinter(printer)
		if document_started:
			win32print.AbortPrinter(printer)
		win32print.ClosePrinter(printer)
