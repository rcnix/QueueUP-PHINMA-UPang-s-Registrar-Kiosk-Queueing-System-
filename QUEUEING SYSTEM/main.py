import argparse
import tkinter.messagebox as messagebox

import customtkinter as ctk
import psycopg2

from application import QueueUPApp
from database.queries import ensure_schema

FONT_FAMILY = "Bahnschrift"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QueueUP queueing system")
    parser.add_argument(
        "screen",
        nargs="?",
        choices=("suite", "admin", "kiosk", "counter", "display"),
        default="suite",
        help="which interface to run (default: suite)",
    )
    parser.add_argument(
        "--counter",
        type=int,
        choices=range(1, 7),
        default=1,
        help="counter number for the counter interface",
    )
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("green")
    ctk.ThemeManager.theme["CTkFont"]["family"] = FONT_FAMILY
    try:
        ensure_schema()
    except psycopg2.Error as error:
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror(
            "Database setup error",
            "Could not prepare PostgreSQL. Check that it is running and that the "
            f".env settings are correct.\n\n{error}",
            parent=root,
        )
        root.destroy()
        return

    if args.screen in {"suite", "admin"}:
        QueueUPApp().mainloop()
    elif args.screen == "kiosk":
        from kiosk.kiosk_window import main as run_screen
        run_screen()
    elif args.screen == "counter":
        from counter.counter_window import main as run_screen
        run_screen(args.counter)
    else:
        from display.display_window import main as run_screen
        run_screen()


if __name__ == "__main__":
    main()