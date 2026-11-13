#!/usr/bin/env python3
"""
make_calendar_v2.0.py — Outlook-style printable calendar PDF (A4 landscape)

Fixes vs v1.9 per your last screenshots:
- TRUE "apparent double lines" = a visible GAP between boxes where they meet.
  (Each compartment has its own border; we leave a small white gap between them.)
- All compartment border lines are the SAME thickness (no doubled-thickness strokes).
- Removes the internal "footer band" completely by extending the 3 boxes down to the
  outer border; page number is printed OUTSIDE the outer border in the page margin.
- Ensures the full-width boundary above the weekday row + Tasks header is present and
  same thickness (because it's simply the top border of the Calendar/Tasks boxes).

Other retained features:
- 3 mini-months (prev/current/next) with outer border only (no internal grid lines).
- UK holidays (England) if python-holidays is installed.
- Week numbers embedded in Monday cells (light grey).
- Weekday-name band height == Tasks header band height.

Usage:
  python3 make_calendar_v2.0.py 2026 --out calendar_2026.pdf
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
    tasks_w = 55 * mm

    # Fixed band height used by BOTH weekday row and Tasks header
    band_h = 6.0 * mm

    # Visible gap between compartment borders (points)
    # (This is the "double-line illusion": two borders with a white gap.)
    gap_pt = 4.0  # ~0.7mm

    # Typography
    font = "Helvetica"
    font_bold = "Helvetica-Bold"
    title_size = 16
    weekday_size = 9
    date_size = 9
    holiday_size = 6.5

    # Line widths (all box borders the same)
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
    gap = s.gap_pt  # points

    uk_hols = build_uk_holidays(year)

    # Outer page border
    set_grey(c, 0.1)
    draw_rect(c, m, m, W - 2 * m, H - 2 * m, lw=s.outer_w)

    # Header box
    header_x = m
    header_w = W - 2 * m
    header_h = s.header_h
    header_y = H - m - header_h

    # Lower area top is separated from header by a visible GAP
    lower_x = m
    lower_w = W - 2 * m
    lower_y = m
    lower_top = header_y - gap
    lower_h = lower_top - lower_y

    # Split Calendar and Tasks with a visible GAP
    split_x = lower_x + (lower_w - s.tasks_w)
    cal_x = lower_x
    cal_y = lower_y
    cal_w = (split_x - gap/2) - cal_x
    cal_h = lower_h

    tasks_x = split_x + gap/2
    tasks_y = lower_y
    tasks_w = (lower_x + lower_w) - tasks_x
    tasks_h = lower_h

    # Background fills
    fill_rect(c, header_x, header_y, header_w, header_h, s.fill_header)

    band_h = s.band_h
    fill_rect(c, cal_x, cal_y + cal_h - band_h, cal_w, band_h, s.fill_band)
    fill_rect(c, tasks_x, tasks_y + tasks_h - band_h, tasks_w, band_h, s.fill_band)

    # Header title
    set_grey(c, 0.0)
    c.setFont(s.font_bold, s.title_size)
    c.drawString(header_x + 6, header_y + header_h - 16, f"{calendar.month_name[month]} {year}")

    # Mini months area
    mini_area_w = 90 * mm
    mini_area_h = 18 * mm
    mini_area_x = header_x + header_w - mini_area_w - 6
    mini_area_y = header_y + 2
    draw_three_mini_months(c, year, month, mini_area_x, mini_area_y, mini_area_w, mini_area_h)

    # Weekday names (calendar band)
    set_grey(c, 0.1)
    c.setFont(s.font_bold, s.weekday_size)
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    cols = 7
    cell_w = cal_w / cols
    weekday_text_y = cal_y + cal_h - band_h / 2 - 3
    for col, name in enumerate(weekdays):
        c.drawCentredString(cal_x + (col + 0.5) * cell_w, weekday_text_y, name)

    # Tasks header + SINGLE underline
    set_grey(c, 0.1)
    c.setFont(s.font_bold, 10)
    c.drawCentredString(tasks_x + tasks_w / 2, tasks_y + tasks_h - band_h / 2 - 3, "Tasks")
    draw_line(c, tasks_x, tasks_y + tasks_h - band_h, tasks_x + tasks_w, tasks_y + tasks_h - band_h, lw=s.grid_w)

    # Calendar weeks (use natural month row count: usually 5, sometimes 6)
    cal_obj = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal_obj.monthdatescalendar(year, month)
    week_rows = len(weeks)

    day_h = (cal_h - band_h) / week_rows

    # Grid lines inside calendar only
    set_grey(c, s.grid_grey)

    # Vertical
    for i in range(cols + 1):
        x = cal_x + i * cell_w
        draw_line(c, x, cal_y, x, cal_y + cal_h, lw=s.grid_w)

    # Horizontal
    draw_line(c, cal_x, cal_y, cal_x + cal_w, cal_y, lw=s.grid_w)
    for r in range(1, week_rows):
        y = cal_y + r * day_h
        draw_line(c, cal_x, y, cal_x + cal_w, y, lw=s.grid_w)
    y_weekday = cal_y + week_rows * day_h
    draw_line(c, cal_x, y_weekday, cal_x + cal_w, y_weekday, lw=s.grid_w)
    draw_line(c, cal_x, cal_y + cal_h, cal_x + cal_w, cal_y + cal_h, lw=s.grid_w)

    # Dates + embedded week numbers (in Monday cells)
    for r, week in enumerate(weeks):
        y0 = cal_y + (week_rows - 1 - r) * day_h
        monday = week[0]
        wn = iso_week_label(monday)

        for col, d in enumerate(week):
            x0 = cal_x + col * cell_w

            if d.month != month:
                set_grey(c, s.other_month_grey)
            else:
                set_grey(c, s.text_grey)

            c.setFont(s.font, s.date_size)
            c.drawString(x0 + 2, y0 + day_h - 12, str(d.day))

            if col == 0:
                set_grey(c, s.weeknum_grey)
                c.setFont(s.font, 6.5)
                c.drawString(x0 + 2, y0 + 2, wn)

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

    # Compartment borders LAST (same thickness everywhere)
    set_grey(c, 0.1)
    draw_rect(c, header_x, header_y, header_w, header_h, lw=s.box_w)
    draw_rect(c, cal_x, cal_y, cal_w, cal_h, lw=s.box_w)
    draw_rect(c, tasks_x, tasks_y, tasks_w, tasks_h, lw=s.box_w)

    # Page number OUTSIDE the outer border (in margin), bottom-right
    set_grey(c, 0.4)
    c.setFont(s.font, 8)
    c.drawRightString(W - m, m - 10,  f"Page {page_num} of {total_pages}")


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
