#!/usr/bin/env python3
"""
make_calendar_v1.8.py — Outlook-style printable calendar PDF (A4 landscape)

Matches user's 2025 Outlook reference more closely:
- Three separate compartment boxes: Header, Calendar, Tasks.
  (Shared borders intentionally appear like "double lines" because boxes are drawn independently.)
- Weekday-name row height == Tasks header height (fixed height).
- Page number is OUTSIDE the three boxes, at bottom-right of the page (inside outer page border).
- Mini-months: outer border only (no internal grid lines).
- Week numbers are embedded in Monday cells (light grey).
- Greyscale fills: header, weekday-name row, tasks header.
- Tasks header underline is a SINGLE line.

Dependencies:
  pip install reportlab
  pip install holidays   (optional; script still runs without it)

Usage:
  python3 make_calendar_v1.8.py 2026 --out calendar_2026.pdf
"""

import argparse
import calendar
import datetime as dt
from dataclasses import dataclass

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

try:
    import holidays  # type: ignore
except Exception:
    holidays = None


@dataclass
class Style:
    page_size = landscape(A4)
    margin = 9 * mm

    # Compartment geometry
    header_h = 20 * mm
    bottom_free_h = 7 * mm          # free strip for page number (outside boxes)
    tasks_w = 55 * mm

    # Fixed band height used by BOTH weekday row and Tasks header
    band_h = 6.0 * mm               # ~17 pts; tweak if desired

    # Typography
    font = "Helvetica"
    font_bold = "Helvetica-Bold"
    title_size = 16
    weekday_size = 9
    date_size = 9
    holiday_size = 6.5
    mini_title_size = 6.5

    # Lines
    outer_w = 1.3
    box_w = 1.0
    grid_w = 0.8

    # Greys
    fill_header = 0.95
    fill_band = 0.92
    weeknum_grey = 0.70
    other_month_grey = 0.70
    text_grey = 0.12
    grid_grey = 0.35


def set_grey(c: canvas.Canvas, v: float):
    c.setStrokeColor(colors.Color(v, v, v))
    c.setFillColor(colors.Color(v, v, v))


def draw_rect(c: canvas.Canvas, x, y, w, h, lw: float):
    c.setLineWidth(lw)
    c.rect(x, y, w, h, stroke=1, fill=0)


def draw_line(c: canvas.Canvas, x1, y1, x2, y2, lw: float):
    c.setLineWidth(lw)
    c.line(x1, y1, x2, y2)


def fill_rect(c: canvas.Canvas, x, y, w, h, grey: float):
    c.saveState()
    c.setFillColor(colors.Color(grey, grey, grey))
    c.setStrokeColor(colors.Color(grey, grey, grey))
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.restoreState()


def iso_week_label(d: dt.date) -> str:
    return f"w{d.isocalendar().week:02d}"


def prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def build_uk_holidays(year: int):
    if holidays is None:
        return {}
    uk = holidays.UnitedKingdom(years=year, subdiv="England")
    return {d: str(name) for d, name in uk.items()}


def draw_mini_month(c: canvas.Canvas, year: int, month: int, x, y, w, h):
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal.monthdatescalendar(year, month)

    # Outer box only (no internal grid lines)
    set_grey(c, 0.1)
    draw_rect(c, x, y, w, h, lw=0.6)

    # Title
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 2, y + h - 8, calendar.month_name[month])

    wd = ["M", "T", "W", "T", "F", "S", "S"]

    top = y + h - 10
    grid_h = h - 12
    rows = len(weeks) + 1
    cols = 7
    cell_w = w / cols
    cell_h = grid_h / rows

    c.setFont("Helvetica", 5.5)
    for i, ch in enumerate(wd):
        set_grey(c, 0.05)
        c.drawCentredString(x + (i + 0.5) * cell_w, top - 0.8 * cell_h, ch)

    c.setFont("Helvetica", 5.2)
    for r, week in enumerate(weeks):
        for col, d in enumerate(week):
            yy = top - (r + 2) * cell_h + 1
            xx = x + col * cell_w
            if d.month != month:
                set_grey(c, 0.7)
            else:
                set_grey(c, 0.1)
            c.drawRightString(xx + cell_w - 1.2, yy, str(d.day))


def draw_three_mini_months(c: canvas.Canvas, year: int, month: int, x, y, w, h):
    py, pm = prev_month(year, month)
    ny, nm = next_month(year, month)
    gap = 2 * mm
    mini_w = (w - 2 * gap) / 3.0
    draw_mini_month(c, py, pm, x, y, mini_w, h)
    draw_mini_month(c, year, month, x + mini_w + gap, y, mini_w, h)
    draw_mini_month(c, ny, nm, x + 2 * (mini_w + gap), y, mini_w, h)


def draw_month_page(c: canvas.Canvas, year: int, month: int, page_num: int, total_pages: int, s: Style):
    W, H = s.page_size
    m = s.margin

    uk_hols = build_uk_holidays(year)

    # Outer page border
    set_grey(c, 0.1)
    draw_rect(c, m, m, W - 2 * m, H - 2 * m, lw=s.outer_w)

    # Header box (full width)
    header_x = m
    header_y = H - m - s.header_h
    header_w = W - 2 * m
    header_h = s.header_h

    # Lower area: calendar + tasks boxes, sitting ABOVE a free strip for page number
    lower_x = m
    lower_y = m + s.bottom_free_h
    lower_w = W - 2 * m
    lower_h = (H - 2 * m) - s.header_h - s.bottom_free_h

    tasks_w = s.tasks_w
    cal_w = lower_w - tasks_w

    cal_x = lower_x
    cal_y = lower_y
    cal_h = lower_h

    tasks_x = cal_x + cal_w
    tasks_y = lower_y
    tasks_h = lower_h

    # Draw the three compartment boxes independently (intentional "double line" look on shared borders)
    set_grey(c, 0.1)
    draw_rect(c, header_x, header_y, header_w, header_h, lw=s.box_w)
    draw_rect(c, cal_x, cal_y, cal_w, cal_h, lw=s.box_w)
    draw_rect(c, tasks_x, tasks_y, tasks_w, tasks_h, lw=s.box_w)

    # Fill header background and title
    fill_rect(c, header_x, header_y, header_w, header_h, s.fill_header)
    set_grey(c, 0.0)
    c.setFont(s.font_bold, s.title_size)
    c.drawString(header_x + 6, header_y + header_h - 16, f"{calendar.month_name[month]} {year}")

    # Mini months (top-right of header)
    mini_area_w = 90 * mm
    mini_area_h = 18 * mm
    mini_area_x = header_x + header_w - mini_area_w - 6
    mini_area_y = header_y + 2
    draw_three_mini_months(c, year, month, mini_area_x, mini_area_y, mini_area_w, mini_area_h)

    # Tasks header band (height == weekday band height)
    band_h = s.band_h
    fill_rect(c, tasks_x, tasks_y + tasks_h - band_h, tasks_w, band_h, s.fill_band)
    set_grey(c, 0.1)
    c.setFont(s.font_bold, 10)
    c.drawCentredString(tasks_x + tasks_w / 2, tasks_y + tasks_h - band_h / 2 - 3, "Tasks")

    # SINGLE underline below Tasks header (inside tasks box)
    set_grey(c, 0.1)
    draw_line(c, tasks_x, tasks_y + tasks_h - band_h, tasks_x + tasks_w, tasks_y + tasks_h - band_h, lw=s.grid_w)

    # Calendar grid: natural week count (usually 5; sometimes 6). We will draw exactly what monthdatescalendar provides.
    cal_obj = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal_obj.monthdatescalendar(year, month)
    week_rows = len(weeks)

    weekday_h = band_h
    day_h = (cal_h - weekday_h) / week_rows
    cols = 7
    cell_w = cal_w / cols

    # Weekday name band fill (same height as Tasks header band)
    fill_rect(c, cal_x, cal_y + cal_h - weekday_h, cal_w, weekday_h, s.fill_band)

    # Weekday names
    set_grey(c, 0.1)
    c.setFont(s.font_bold, s.weekday_size)
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_text_y = cal_y + cal_h - weekday_h / 2 - 3
    for col, name in enumerate(weekdays):
        c.drawCentredString(cal_x + (col + 0.5) * cell_w, weekday_text_y, name)

    # Calendar grid lines
    set_grey(c, s.grid_grey)

    # Vertical lines
    for i in range(cols + 1):
        x = cal_x + i * cell_w
        draw_line(c, x, cal_y, x, cal_y + cal_h, lw=s.grid_w)

    # Horizontal lines: bottom, week separators, weekday divider, top
    draw_line(c, cal_x, cal_y, cal_x + cal_w, cal_y, lw=s.grid_w)
    for r in range(1, week_rows):
        y = cal_y + r * day_h
        draw_line(c, cal_x, y, cal_x + cal_w, y, lw=s.grid_w)

    y_weekday = cal_y + week_rows * day_h
    draw_line(c, cal_x, y_weekday, cal_x + cal_w, y_weekday, lw=s.grid_w)
    draw_line(c, cal_x, cal_y + cal_h, cal_x + cal_w, cal_y + cal_h, lw=s.grid_w)

    # Populate dates + embedded week numbers in Monday cells
    for r, week in enumerate(weeks):
        # r=0 is top week in monthdatescalendar. Compute row from top.
        y0 = cal_y + (week_rows - 1 - r) * day_h
        monday = week[0]
        wn = iso_week_label(monday)

        for col, d in enumerate(week):
            x0 = cal_x + col * cell_w

            # date colour
            if d.month != month:
                set_grey(c, s.other_month_grey)
            else:
                set_grey(c, s.text_grey)

            c.setFont(s.font, s.date_size)
            c.drawString(x0 + 2, y0 + day_h - 12, str(d.day))

            # week number inside Monday cell, light grey
            if col == 0:
                set_grey(c, s.weeknum_grey)
                c.setFont(s.font, 6.5)
                c.drawString(x0 + 2, y0 + 2, wn)

            # holiday labels (only on in-month days)
            if d.month == month and d in uk_hols:
                set_grey(c, 0.05)
                c.setFont(s.font, s.holiday_size)
                name = uk_hols[d]
                max_chars = 18
                lines = []
                while name and len(lines) < 2:
                    lines.append(name[:max_chars])
                    name = name[max_chars:]
                ty = y0 + day_h - 22
                for ln in lines:
                    c.drawString(x0 + 2, ty, ln)
                    ty -= 7

    # Page number OUTSIDE the three boxes (bottom-right corner, inside outer border)
    set_grey(c, 0.4)
    c.setFont(s.font, 8)
    c.drawRightString(W - m - 6, m + 3, f"Page {page_num} of {total_pages}")


def build_pdf(year: int, out_path: str):
    s = Style()
    c = canvas.Canvas(out_path, pagesize=s.page_size)
    for i, month in enumerate(range(1, 13), start=1):
        draw_month_page(c, year, month, i, 12, s)
        c.showPage()
    c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"calendar_{args.year}.pdf"
    build_pdf(args.year, out)
    print(f"Created: {out}")


if __name__ == "__main__":
    main()
