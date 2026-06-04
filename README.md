# Arabic PDF Reader

A desktop PDF reader built for **madrassah students** reading Arabic books — especially **scanned PDFs** that normal readers cannot select or highlight.

## Features

- Open PDF files and navigate (prev/next, go to page, zoom)
- **Offline Arabic OCR** for scanned pages (Tesseract)
- Select and **copy** OCR text (RTL-aware clipboard)
- **Highlight** passages for research
- **Sticky notes** pinned on the page (Adobe-style)
- **Page notes** — summary text tied to a page number
- **Bookmarks** with sidebar navigation
- **Search** notes and highlights
- All annotations saved in a sidecar file: `yourbook.pdf.apr.json`

## Requirements

- Windows 10/11
- Python 3.10 or newer
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) with **Arabic** language pack

### Install Tesseract (Windows)

1. Download the installer from [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. During setup, select **Arabic** (`ara`) under additional languages.
3. Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

If Tesseract is not on your PATH, you can set it in code (see `core/ocr_service.py`) or add Tesseract to your system PATH.

## Setup

```powershell
cd c:\Users\j4jam\.arabic_pdf_reader
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Project structure

```
main.py              ← start here (entry point)
core/                ← PDF, OCR, saving data (no buttons)
ui/                  ← windows, toolbar, viewer, sidebar
data/                ← OCR cache + recent files (auto-created)
```

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open PDF |
| Ctrl+G | Go to page |
| Ctrl+D | Bookmark current page |
| Ctrl+Left / Ctrl+Right | Previous / next page |
| Ctrl+C | Copy selected OCR text |

## How to use scanned books

1. Open your PDF.
2. Go to a page — if status says **"Scanned page"**, click **OCR Page**.
3. Wait a few seconds (first time only; results are cached).
4. Drag on text areas to **highlight**, or click a word and **Ctrl+C** to copy.
5. Use **Sticky Note** or **Page Note** for research notes.
6. Click **★ Bookmark** for important pages — find them in the sidebar.

## Learning the code

Each file has detailed comments explaining:

- What the file does
- What `self` and `.` mean in that file
- How UI signals connect to handler methods
- **What each import/library does** (see per-file comments + master guide below)

**Start here for imports:** open [`imports_guide.py`](imports_guide.py) — a comment-only file listing every library and class.

Read source files in this order:

1. `main.py`
2. `ui/main_window.py`
3. `core/pdf_document.py`
4. `ui/pdf_viewer.py`

## License

Personal/educational project — use and modify freely.
