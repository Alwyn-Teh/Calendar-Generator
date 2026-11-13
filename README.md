# Calendar Generator

A printable, Outlook-style **12-page A4 landscape PDF calendar** written in Python.

The current generator (`make_calendar.py`) is based on **v3.1**. Each month has a large calendar grid, ISO week numbers, a tasks area, and three mini-calendars (previous/current/next month). It highlights England & Wales bank holidays and shades weekends and dates outside the month.

## Repository contents

- `make_calendar.py` — current generator (v3.1 layout, with updated usage/history header).
- `versions/` — preserved historical scripts, v1.0–v3.1 (only versions actually present in the original archive).
- `calendar_2026.pdf`, `calendar_2027.pdf` — example PDFs from the original archive.
- `requirements.txt` — Python dependencies for the current **and historical** scripts.
- `.gitignore` — excludes local Python environments, caches, and macOS metadata.
- `scripts/check_setup.py` — checks Python dependencies and validates source syntax without generating files.

## Quick start (macOS)

**1. Install Python 3 if needed.** Check first:

```bash
python3 --version
```

If Python 3 is missing, install [Homebrew](https://brew.sh/) and then run:

```bash
brew install python
```

Homebrew itself can be installed with the official command (check [brew.sh](https://brew.sh/) first):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

You **do not** need Homebrew if you already have a suitable Python 3 installation. GitHub Desktop is sufficient to clone and publish the repository; `gh` (GitHub CLI) is not required.

**2. Download or clone the repository.** In GitHub Desktop use **File → Clone Repository…**, select this repository, and choose a local path; or download a ZIP from GitHub's **Code** menu. Open Terminal in the downloaded project directory.

**3. Create and activate a virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**4. Install packages and check setup:**

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_setup.py
```

**5. Generate a calendar:**

```bash
python make_calendar.py 2027 calendar_2027.pdf
open calendar_2027.pdf
```

To generate a calendar using the default filename `calendar_2028.pdf`:

```bash
python make_calendar.py 2028
```

The output file is written to the current working directory. If you use a filename that already exists, it will be overwritten: choose a different output filename to preserve the provided example PDFs.

When finished, use `deactivate` to leave the virtual environment. On subsequent visits, run `source .venv/bin/activate` again before using the generator.

## Linux and Windows

On Linux, use an installed Python 3 with `venv`, follow the same virtual-environment and installation commands, and open the resulting PDF with your preferred viewer (rather than macOS `open`).

On Windows PowerShell, create the environment with `py -m venv .venv`, activate with `.\.venv\Scripts\Activate.ps1`, then run `python -m pip install -r requirements.txt` and `python make_calendar.py 2027 calendar_2027.pdf`. If PowerShell blocks activation, use `.venv\Scripts\python.exe` explicitly to run pip and the script instead.

## Historical versions

Older scripts are kept unchanged in `versions/`. Their command-line options differ: some use `--out`, while later ones accept an optional output filename as a positional argument. To run a historical version, inspect its header or execute `python versions/<filename>.py --help` **only where the script supports `--help`**. The `holidays` package is used by some older scripts; the current script calculates its bank holidays internally and only imports `reportlab` externally.

**Bank-holiday caveat:** the current script implements a standard England & Wales holiday schedule but does not encode all exceptional one-off changes to public holidays (such as special events). Check official dates for the year you print.

## Publishing with GitHub Desktop

Place this repository in your preferred local development folder, e.g. `~/dev/GitHub/Calendar-Generator`. In GitHub Desktop, add the local repository (or create a new GitHub repository), review **Changes**, enter a commit summary, click **Commit to main**, then **Publish repository** or **Push origin** as appropriate. Do not commit `.venv` or macOS metadata.

## Licensing

No open-source licence has been added automatically. The repository owner should choose and add a `LICENSE` file if they want to grant others permission to reuse, modify, or redistribute the code. A public GitHub repository alone is not an open-source licence.
