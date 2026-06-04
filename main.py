# main.py — Entry point for Arabic PDF Reader
# ---------------------------------------------------------------------------
# This is the ONLY file you run directly:  python main.py
#
# Its job is tiny:
#   1. Create the Qt application object (manages the whole GUI lifecycle)
#   2. Create our MainWindow (the main window you see)
#   3. Show the window
#   4. Start the "event loop" (waits for clicks, keys, etc.)
#
# Called by: you (the user) from the terminal
# Calls: ui.main_window.MainWindow
#
# Library reference: see imports_guide.py in the project root.

# --- Python built-in: sys ---
# sys.argv  = list of command-line arguments (e.g. ["main.py"])
# sys.exit  = quit program with an exit code (used via SystemExit below)
import sys

# --- PySide6.QtWidgets.QApplication ---
# The single "application" object for the whole GUI program.
# Must exist before any window; app.exec() runs the event loop (clicks, keys).
# Qt needs sys.argv for platform-specific initialization on some OSes.
from PySide6.QtWidgets import QApplication

# --- Our code: ui.main_window.MainWindow ---
# MainWindow = class defined in ui/main_window.py (the big window with toolbar).
# "from ui.main_window import MainWindow" opens that file and brings the name here.
from ui.main_window import MainWindow


def main() -> int:
    """
    Create and run the application.

    Returns:
        int: Exit code (0 = success). Passed back to the operating system.
    """
    # QApplication is the top-level Qt object — there must be exactly one
    # per program. It handles fonts, styles, and the event loop.
    app = QApplication(sys.argv)

    # Set application metadata (shows in taskbar tooltip on some systems).
    app.setApplicationName("Reader")
    app.setOrganizationName("ArabicPDFReader")

    # Create an INSTANCE of MainWindow (our class).
    # window is a variable holding the object; window.show() calls a METHOD on it.
    window = MainWindow()
    window.show()  # Make the window visible on screen.

    # app.exec() starts the event loop — the program "runs" until you close the window.
    # While running, Qt watches for mouse clicks, key presses, etc. and calls our code.
    return app.exec()


# This block runs ONLY when you execute: python main.py
# It does NOT run if another file imports main.py as a module.
if __name__ == "__main__":
    # SystemExit is a built-in exception that ends the program cleanly.
    # main() returns app.exec()'s exit code (0 = normal quit).
    # raise SystemExit(...) passes that code back to the terminal/OS.
    raise SystemExit(main())
