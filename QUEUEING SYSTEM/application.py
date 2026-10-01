import customtkinter as ctk

from assets import set_window_icon


class QueueUPApp(ctk.CTk):
	def __init__(self) -> None:
		super().__init__()
		self.title("QueueUP: PHINMA-UPang's Registrar Queueing System")
		self.geometry("1280x820")
		self.minsize(980, 640)
		set_window_icon(self)

		tabs = ctk.CTkTabview(self)
		tabs.pack(fill="both", expand=True, padx=12, pady=12)
		for name in ("Admin", "Kiosk", "Counter Simulation", "Counter Interface"):
			tabs.add(name)

		from admin.admin_window import MainFrame
		from admin.dashboard import AdminDashboard
		from counter.counter_window import CounterControls
		from kiosk.kiosk_window import KioskWindow

		AdminDashboard(tabs.tab("Admin"))
		KioskWindow(tabs.tab("Kiosk")).pack(fill="both", expand=True)
		MainFrame(tabs.tab("Counter Simulation"))
		CounterControls(tabs.tab("Counter Interface")).pack(fill="both", expand=True)