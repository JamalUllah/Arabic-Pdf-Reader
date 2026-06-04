# imports_guide.py — Library & import reference (read this file to learn)
# =============================================================================
# This file is COMMENTS ONLY — it is never imported by the app.
# Open it in your editor whenever you wonder "what does this import do?"
#
# HOW TO READ IMPORT LINES
# ------------------------
#   from PySide6.QtWidgets import QApplication
#         |         |            |
#      package   submodule      class (or function)
#
#   import fitz          → whole module; use as fitz.open()
#   from x import Y      → bring just Y into this file
#
# =============================================================================
# EXTERNAL PACKAGES (installed via: pip install -r requirements.txt)
# =============================================================================
#
# --- PySide6 (Qt for Python) — the entire graphical user interface ---
# Sub-modules we use:
#
#   PySide6.QtWidgets — visible UI widgets
#     QApplication    : The one app object; starts the event loop (main.py)
#     QMainWindow     : Main window frame with toolbar area + central widget
#     QToolBar        : Row of buttons at the top (ReaderToolbar)
#     QPushButton     : Clickable button (Open, Prev, Next, OCR…)
#     QLineEdit       : Single-line text box (page number, search)
#     QComboBox       : Dropdown list (zoom levels)
#     QLabel          : Static text label (" / 842 pages")
#     QStatusBar      : Bottom status line ("Opened: book.pdf")
#     QFileDialog     : Native file picker dialog (Open PDF)
#     QMessageBox     : Alert / warning / error popup
#     QProgressDialog : Progress bar while OCR runs on all pages
#     QGraphicsView   : Scrollable canvas that displays the PDF page
#     QGraphicsScene  : Holds drawable items (page image, highlights, pins)
#     QGraphicsRectItem   : Rectangle on the canvas (highlight selection)
#     QGraphicsEllipseItem: Circle on the canvas (sticky note pin)
#     QDialog         : Small popup window (go to page, edit note)
#     QDialogButtonBox: Standard OK / Cancel buttons on dialogs
#     QTextEdit       : Multi-line text editor (Arabic notes, RTL)
#     QSpinBox        : Number picker (go to page #)
#     QListWidget     : Scrollable list (sidebar bookmarks / notes)
#     QListWidgetItem : One row in QListWidget
#     QTabWidget      : Tabbed panel (Bookmarks | Notes | Highlights)
#     QWidget         : Generic container widget
#     QVBoxLayout     : Stack widgets vertically
#     QHBoxLayout     : Stack widgets horizontally
#     QFormLayout     : Label + field rows (go-to-page dialog)
#
#   PySide6.QtCore — events, threading, constants
#     Signal          : Custom event you define ("button_clicked = Signal()")
#     Slot            : Marks a method Qt can invoke from a thread
#     QObject         : Base class for objects that use signals (OcrWorker)
#     QThread         : Background thread so OCR does not freeze the UI
#     Qt              : Namespace of constants (RightToLeft, mouse buttons, etc.)
#     QPointF         : A point (x, y) with float coordinates (mouse position)
#
#   PySide6.QtGui — images, colors, keyboard, menus
#     QPixmap         : Image ready to draw on screen (PDF page)
#     QImage          : Raw image data; converts PNG bytes → pixmap
#     QColor          : Color with red/green/blue/alpha (highlight yellow)
#     QBrush          : Fill color/style for shapes
#     QPen            : Line / border style for shapes
#     QPainter        : Rendering hints (smooth zoom, anti-aliasing)
#     QAction         : One menu item (File → Open)
#     QKeySequence    : Describes a keyboard shortcut (Ctrl+O, Ctrl+G)
#     QShortcut       : Binds a key press to a Python function
#
# --- PyMuPDF (imported as fitz) — PDF engine ---
#     fitz.open()     : Opens a PDF file from disk
#     fitz.Document   : The open PDF (pages, metadata)
#     fitz.Matrix     : Scale/zoom when rendering a page to pixels
#     page.get_text() : Extract embedded text (empty on scanned pages)
#     page.get_pixmap(): Turn one page into a bitmap image
#
# --- pytesseract — Python bridge to Tesseract OCR program ---
#     image_to_data() : Returns every word + bounding box on a page
#     get_tesseract_version() : Checks Tesseract is installed
#     TesseractNotFoundError  : Raised when Tesseract exe is missing
#   NOTE: You must install Tesseract separately on Windows (not via pip).
#
# --- Pillow (PIL) — image handling ---
#     PIL.Image       : Image object Tesseract accepts as input
#     Image.open()    : Load PNG bytes (from PyMuPDF) into an Image
#
# --- arabic-reshaper — Arabic letter shaping ---
#     reshape()       : Connects Arabic letters (initial/medial/final forms)
#
# --- python-bidi (bidi.algorithm) — right-to-left text ---
#     get_display()   : Reorders characters so Arabic reads RTL on screen
#
# =============================================================================
# PYTHON BUILT-IN MODULES (come with Python — no pip install)
# =============================================================================
#
#   sys             : sys.argv (command-line args), exit codes
#   json            : json.load / json.dump — read/write .json files
#   pathlib.Path    : Clean file paths: Path("data") / "cache.json"
#   dataclasses     : @dataclass — easy data-only classes (Highlight, OcrWord)
#                     field() — default values; asdict() — convert to dict
#   datetime        : Timestamps on saved notes and bookmarks
#   typing          : Type hints (Callable, Any) — documentation for readers
#   enum            : Enum / auto — named constants (ToolMode.NAVIGATE)
#   __future__.annotations : Allows modern type hints like str | None
#
# =============================================================================
# OUR OWN MODULES (code we wrote in this project)
# =============================================================================
#
#   core/pdf_document.py
#     PdfDocument     : Open PDF, render pages, detect scanned pages
#
#   core/ocr_service.py
#     OcrWord         : One OCR word + position (dataclass)
#     OcrResult       : All words from one page
#     OcrCache        : Save/load OCR results to disk (avoid re-running)
#     run_ocr_on_image(): Plain function — runs Tesseract on one image
#     check_tesseract_installed(): Plain function — is Tesseract available?
#
#   core/text_layer.py
#     shape_arabic_for_display()  : Fix Arabic for on-screen text
#     shape_arabic_for_clipboard(): Fix Arabic before copying
#     words_to_full_text()        : Join OCR words into one string
#     find_words_in_rect()        : Words inside a drag-selection box
#
#   core/annotation_store.py
#     AnnotationStore : Load/save all highlights, notes, bookmarks
#     Highlight       : One colored highlight region
#     StickyNote      : Pin note at x,y on a page
#     PageNote        : Summary note for a page number
#     Bookmark        : Saved page shortcut
#
#   ui/main_window.py
#     MainWindow      : Top window; wires toolbar + viewer + sidebar
#     OcrWorker       : Runs OCR in a background QThread
#
#   ui/pdf_viewer.py
#     PdfViewer       : Shows PDF page; highlight & sticky-note tools
#     ToolMode        : Enum — NAVIGATE | HIGHLIGHT | STICKY_NOTE
#
#   ui/toolbar.py
#     ReaderToolbar   : All top buttons; emits Signal events
#
#   ui/sidebar.py
#     Sidebar         : Lists bookmarks, notes, highlights
#
#   ui/note_dialog.py
#     StickyNoteDialog, PageNoteDialog, GoToPageDialog, BookmarkTitleDialog
#
# =============================================================================
# WHICH LIBRARY FOR WHICH JOB?
# =============================================================================
#
#   Show windows and buttons     → PySide6
#   Open PDF and render pages    → PyMuPDF (fitz)
#   Read text from scanned pages → Tesseract + pytesseract + Pillow
#   Display/copy Arabic correctly→ arabic-reshaper + python-bidi
#   Save highlights and notes    → json + AnnotationStore
#   File paths on disk           → pathlib.Path
#
# =============================================================================

# This module intentionally defines nothing — it exists only as documentation.
