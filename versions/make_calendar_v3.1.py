#!/usr/bin/env python3
"""
Outlook-style yearly month-per-page calendar (A4) with:
- 3 compartment boxes: Header, Month grid, Tasks
- Visible "double line" effect via small *gaps* between compartment borders
- 3 mini-months (prev/current/next) in header right
- UK (England & Wales) bank holidays
- Adaptive 5/6 week rows per month (based on month layout)

Usage:
  python3 make_calendar_v2.7.py 2026
  python3 make_calendar_v2.7.py 2026 out.pdf
"""

from __future__ import annotations
import calendar
import datetime as _dt
import sys
from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors


# -------------------- Holidays (England & Wales) --------------------

def _easter_sunday(year: int) -> _dt.date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return _dt.date(year, month, day)


def _first_monday(year: int, month: int) -> _dt.date:
    d = _dt.date(year, month, 1)
    while d.weekday() != 0:  # Monday
        d += _dt.timedelta(days=1)
    return d


def _last_monday(year: int, month: int) -> _dt.date:
    # Start from last day of month
    last_day = calendar.monthrange(year, month)[1]
    d = _dt.date(year, month, last_day)
    while d.weekday() != 0:
        d -= _dt.timedelta(days=1)
    return d


def uk_bank_holidays_england_wales(year: int) -> dict[_dt.date, str]:
    """
    Minimal, dependency-free UK bank holidays (England & Wales).
    Includes observed dates when holidays fall on a weekend.
    Note: Special one-off historical changes (e.g. 2022) are not encoded.
    """
    hols: dict[_dt.date, str] = {}

    def add(date: _dt.date, name: str):
        hols[date] = name

    def add_observed_if_weekend(date: _dt.date, name: str):
        add(date, name)
        if date.weekday() == 5:  # Sat -> observed Monday
            add(date + _dt.timedelta(days=2), f"{name} (observed)")
        elif date.weekday() == 6:  # Sun -> observed Monday
            add(date + _dt.timedelta(days=1), f"{name} (observed)")

    # New Year's Day
    add_observed_if_weekend(_dt.date(year, 1, 1), "New Year's Day")

    # Easter-related
    easter = _easter_sunday(year)
    add(easter - _dt.timedelta(days=2), "Good Friday")
    add(easter + _dt.timedelta(days=1), "Easter Monday")

    # May holidays
    add(_first_monday(year, 5), "Early May bank holiday")
    add(_last_monday(year, 5), "Spring bank holiday")

    # Summer bank holiday (last Monday in August)
    add(_last_monday(year, 8), "Summer bank holiday")

    # Christmas / Boxing Day with UK observation rules interaction
    xmas = _dt.date(year, 12, 25)
    boxing = _dt.date(year, 12, 26)
    add(xmas, "Christmas Day")
    add(boxing, "Boxing Day")

    # Observed days:
    if xmas.weekday() == 5:  # Sat
        add(_dt.date(year, 12, 27), "Christmas Day (observed)")
        add(_dt.date(year, 12, 28), "Boxing Day (observed)")
    elif xmas.weekday() == 6:  # Sun
        add(_dt.date(year, 12, 27), "Christmas Day (observed)")
        # Boxing Day is Monday 26 (already weekday) so no extra
    else:
        # Christmas is weekday; Boxing day could be weekend in rare calendar? (Only if xmas is Fri? then boxing Sat)
        if boxing.weekday() == 5:  # Sat
            add(_dt.date(year, 12, 28), "Boxing Day (observed)")
        elif boxing.weekday() == 6:  # Sun
            add(_dt.date(year, 12, 28), "Boxing Day (observed)")

    return hols


# -------------------- Layout & drawing --------------------

@dataclass
class Style:
    # Page / margins
    margin: float = 10 * mm

    # Gaps between compartment borders (to create "double line" appearance)
    gap_h: float = 1.5 * mm       # gap between header box and grid/tasks boxes (vertical)
    gap_v: float = 1.2 * mm       # gap between calendar box and tasks box (horizontal)

    # Line weights / colours
    border_w: float = 0.6         # compartment border (match grid weight)
    grid_w: float = 0.6           # grid internal lines
    mini_w: float = 0.35          # mini-month border lines
    border_grey: float = 0.10
    grid_grey: float = 0.35
    mini_grey: float = 0.55

    # Header proportions
    header_h: float = 26 * mm
    title_font: str = "Helvetica-Bold"
    title_size: float = 18

    # Day name row / tasks header
    dow_h: float = 9 * mm
    tasks_header_h: float = 9 * mm
    header_fill_grey: float = 0.92  # for DOW + Tasks header

    # Cell background fills (subtle)
    weekend_fill_grey: float = 0.965      # Saturday/Sunday columns
    other_month_fill_grey: float = 0.972  # dates from adjacent months

    dow_font: str = "Helvetica-Bold"
    dow_size: float = 9

    day_num_font: str = "Helvetica"
    day_num_size: float = 9

    holiday_font: str = "Helvetica"
    holiday_size: float = 6.5

    weeknum_font: str = "Helvetica"
    weeknum_size: float = 6.5
    weeknum_grey: float = 0.55

    page_font: str = "Helvetica"
    page_size: float = 9

    # Mini months
    # Make the mini-month strip slightly wider so month+year can fit comfortably.
    # The mini boxes will be rectangular if needed.
    mini_months_w: float = 78 * mm
    mini_months_h: float = 22 * mm
    mini_title_size: float = 7
    mini_day_size: float = 6


def _set_stroke(c: canvas.Canvas, w: float, g: float):
    c.setLineWidth(w)
    c.setStrokeColor(colors.Color(g, g, g))


def _set_fill_grey(c: canvas.Canvas, g: float):
    c.setFillColor(colors.Color(g, g, g))


def _draw_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float, lw: float, grey: float, fill_grey: float | None = None):
    _set_stroke(c, lw, grey)
    if fill_grey is None:
        c.setFillColor(colors.white)
        c.rect(x, y, w, h, stroke=1, fill=0)
    else:
        _set_fill_grey(c, fill_grey)
        c.rect(x, y, w, h, stroke=1, fill=1)


def _draw_text(c: canvas.Canvas, x: float, y: float, s: str, font: str, size: float, grey: float = 0.0):
    c.setFont(font, size)
    _set_fill_grey(c, grey)
    c.drawString(x, y, s)


def _month_weeks(year: int, month: int) -> list[list[int]]:
    cal = calendar.Calendar(firstweekday=0)  # Monday
    # monthdayscalendar yields lists of 7 ints, 0 for padding, weeks vary 4..6
    return cal.monthdayscalendar(year, month)


def _prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _draw_mini_month(c: canvas.Canvas, year: int, month: int, x: float, y: float, w: float, h: float, s: Style):
    # Simple mini-month: title + 7 columns, up to 6 rows. No internal grid lines (only border).
    _draw_rect(c, x, y, w, h, lw=s.mini_w, grey=s.mini_grey, fill_grey=None)

    # Title: "Month YYYY" centered
    title = f"{calendar.month_name[month]} {year}"
    c.setFont("Helvetica", s.mini_title_size)
    _set_fill_grey(c, 0.0)
    c.drawCentredString(x + w/2.0, y + h - 3.5*mm, title)

    # Day letters
    letters = ["M","T","W","T","F","S","S"]
    c.setFont("Helvetica", s.mini_day_size)
    lx = x + 1.2*mm
    top = y + h - 6.8*mm
    col_w = (w - 2.4*mm) / 7.0
    for i, ch in enumerate(letters):
            c.drawCentredString(lx + i*col_w + col_w/2.0, top, ch)

    weeks = _month_weeks(year, month)
    # Numbers
    num_top = top - 2.8*mm
    row_h = (h - 9.8*mm) / max(4, len(weeks))  # stable sizing
    for r, wk in enumerate(weeks):
        for i, d in enumerate(wk):
            if d == 0:
                continue
            # Right-justify dates so single/double digits align nicely
            c.drawRightString(lx + (i+1)*col_w - 0.6*mm, num_top - r*row_h, str(d))


def _draw_mini_months_block(c: canvas.Canvas, year: int, month: int, x: float, y: float, s: Style):
    # 3 mini months placed with thin grey borders; no internal grid lines.
    block_w = s.mini_months_w
    block_h = s.mini_months_h
    # No outer box; each mini-month boxed
    pm_y, pm_m = _prev_month(year, month)
    nm_y, nm_m = _next_month(year, month)
    each_w = (block_w - 2*mm) / 3.0
    _draw_mini_month(c, pm_y, pm_m, x, y, each_w, block_h, s)
    _draw_mini_month(c, year, month, x + each_w + 1*mm, y, each_w, block_h, s)
    _draw_mini_month(c, nm_y, nm_m, x + 2*(each_w + 1*mm), y, each_w, block_h, s)


def draw_month_page(c: canvas.Canvas, year: int, month: int, page_num: int, total_pages: int, s: Style):
    W, H = landscape(A4)
    m = s.margin

    # Compartment geometry
    header_x = m
    header_y = H - m - s.header_h
    header_w = W - 2*m
    header_h = s.header_h

    # Body compartments start below header with a GAP so you see "double line"
    body_top = header_y - s.gap_h
    # Leave a little room at bottom so boxes never touch the page number area
    body_bottom = m + 4*mm
    # Page number: vertically centered between bottom of tasks box and bottom of page
    page_num_y = body_bottom / 2.0

    body_h = body_top - body_bottom

    # Tasks width and gap between calendar and tasks
    tasks_w = 52 * mm
    gap_v = s.gap_v
    cal_w = header_w - tasks_w - gap_v

    cal_x = m
    tasks_x = cal_x + cal_w + gap_v

    cal_y = body_bottom
    cal_h = body_h

    tasks_y = body_bottom
    tasks_h = body_h

    # HEADER box (full width)
    _draw_rect(c, header_x, header_y, header_w, header_h, lw=s.border_w, grey=s.border_grey, fill_grey=0.94)

    # Title
    title = f"{calendar.month_name[month]} {year}"
    c.setFont(s.title_font, s.title_size)
    _set_fill_grey(c, 0.0)
    c.drawString(header_x + 4*mm, header_y + header_h - 10*mm, title)

    # Mini months (top right inside header)
    mini_x = header_x + header_w - s.mini_months_w - 4*mm
    mini_y = header_y + (header_h - s.mini_months_h) / 2.0  # centre mini-months vertically
    _draw_mini_months_block(c, year, month, mini_x, mini_y, s)

    # CALENDAR box and TASKS box (separate, with a GAP between => double line look)
    _draw_rect(c, cal_x, cal_y, cal_w, cal_h, lw=s.border_w, grey=s.border_grey, fill_grey=None)
    _draw_rect(c, tasks_x, tasks_y, tasks_w, tasks_h, lw=s.border_w, grey=s.border_grey, fill_grey=None)

    # Day-of-week header row (inside calendar box)
    dow_y = cal_y + cal_h - s.dow_h
    # Fill background without stroking (avoids doubled/thicker edges)
    _set_fill_grey(c, s.header_fill_grey)
    c.rect(cal_x, dow_y, cal_w, s.dow_h, stroke=0, fill=1)
    # Bottom separator line under DOW row
    _set_stroke(c, s.grid_w, s.grid_grey)
    c.line(cal_x, dow_y, cal_x + cal_w, dow_y)
    # Vertical separators within DOW row
    col_w = cal_w / 7.0
    for i in range(1, 7):
        x = cal_x + i*col_w
        c.line(x, dow_y, x, dow_y + s.dow_h)

    # Tasks header row (inside tasks box)
    th_y = tasks_y + tasks_h - s.tasks_header_h
    _set_fill_grey(c, s.header_fill_grey)
    c.rect(tasks_x, th_y, tasks_w, s.tasks_header_h, stroke=0, fill=1)
    # Bottom separator line under Tasks header
    _set_stroke(c, s.grid_w, s.grid_grey)
    c.line(tasks_x, th_y, tasks_x + tasks_w, th_y)

    c.setFont("Helvetica-Bold", 10)
    _set_fill_grey(c, 0.0)
    c.drawCentredString(tasks_x + tasks_w/2, th_y + s.tasks_header_h/2 - 3, "Tasks")

    # Column widths
    col_w = cal_w / 7.0

    # DOW labels
    dows = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    c.setFont(s.dow_font, s.dow_size)
    _set_fill_grey(c, 0.0)
    for i, name in enumerate(dows):
        cx = cal_x + i*col_w
        c.drawCentredString(cx + col_w/2, dow_y + s.dow_h/2 - 3, name)

    # Month grid area below DOW row
    grid_top = dow_y
    grid_bottom = cal_y
    grid_h = grid_top - grid_bottom

    weeks = _month_weeks(year, month)
    nrows = len(weeks)  # 4..6
    row_h = grid_h / nrows

    # Determine the Monday on/before the 1st so we can map each grid cell to a real date
    first_of_month = _dt.date(year, month, 1)
    start = first_of_month - _dt.timedelta(days=first_of_month.weekday())  # Monday=0

    # Background fills (draw BEFORE grid lines so lines stay crisp)
    for r in range(nrows):
        row_y_top = grid_top - r*row_h
        row_y_bottom = row_y_top - row_h
        monday_date = start + _dt.timedelta(days=r*7)
        for i in range(7):
            cell_x = cal_x + i*col_w
            cell_y = row_y_bottom
            d = monday_date + _dt.timedelta(days=i)
            fill = None
            if d.month != month:
                fill = s.other_month_fill_grey
            elif i >= 5:  # Saturday/Sunday columns
                fill = s.weekend_fill_grey
            if fill is not None:
                _set_fill_grey(c, fill)
                c.rect(cell_x, cell_y, col_w, row_h, stroke=0, fill=1)

    # Internal vertical lines (grid)
    for i in range(1, 7):
        x = cal_x + i*col_w
        _set_stroke(c, s.grid_w, s.grid_grey)
        c.line(x, grid_bottom, x, grid_top)

    # Internal horizontal lines
    for r in range(1, nrows):
        y = grid_bottom + r*row_h
        _set_stroke(c, s.grid_w, s.grid_grey)
        c.line(cal_x, y, cal_x + cal_w, y)

    # Week numbers (ISO) placed "inside first weekday column left to the date", greyed
    # We'll place week number near left edge, mid-ish vertically of each row.
    hols = uk_bank_holidays_england_wales(year)

    # Determine dates for each cell (including prev/next month spill)
    for r, wk in enumerate(weeks):
        row_y_top = grid_top - r*row_h
        row_y_bottom = row_y_top - row_h

        # ISO week label based on Monday of that row
        monday_date = start + _dt.timedelta(days=r*7)
        iso_week = monday_date.isocalendar().week
        c.setFont(s.weeknum_font, s.weeknum_size)
        _set_fill_grey(c, s.weeknum_grey)
        c.drawString(cal_x + 1.2*mm, row_y_top - 10*mm, f"w{iso_week:02d}")

        for i in range(7):
            cell_x = cal_x + i*col_w
            cell_y = row_y_bottom
            # Date for this cell:
            d = monday_date + _dt.timedelta(days=i)
            in_month = (d.month == month)

            # Day number
            c.setFont(s.day_num_font, s.day_num_size)
            _set_fill_grey(c, 0.0 if in_month else 0.55)
            c.drawString(cell_x + 1.4*mm, row_y_top - 8*mm, str(d.day))

            # Holiday label (only if in target month OR observed within month)
            label = hols.get(d)
            if label:
                c.setFont(s.holiday_font, s.holiday_size)
                _set_fill_grey(c, 0.0)
                # Place under day number
                c.drawString(cell_x + 1.4*mm, row_y_top - 13*mm, label)

    # Page number outside all boxes (bottom-right)
    c.setFont(s.page_font, s.page_size)
    _set_fill_grey(c, 0.0)
    c.drawRightString(W - m, page_num_y, f"Page {page_num} of {total_pages}")


def build_pdf(year: int, out_path: Path):
    c = canvas.Canvas(str(out_path), pagesize=landscape(A4))
    s = Style()
    total = 12
    for m in range(1, 13):
        draw_month_page(c, year, m, m, total, s)
        c.showPage()
    c.save()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    year = int(argv[1])
    out = Path(argv[2]) if len(argv) > 2 else Path(f"calendar_{year}.pdf")
    build_pdf(year, out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))