#!/usr/bin/env python3
"""
make_calendar.py (v1.6) — Outlook-ish printable calendar PDF generator.

Features:
- A4 landscape
- 1 month per page (12 pages)
- Monday-first, 6 week rows
- Week number (e.g. w01) shown INSIDE Monday cell (light grey)
- Tasks column on the right (blank writing area)
- 3 mini months in header (prev/current/next) top-right (no internal grid lines)
- UK public holidays (England/Wales) placed inside current-month day cells
- Separate boxed compartments: Header box, Calendar box, Tasks box
- Greyscale fills for header band + weekday-name band + tasks header band

Usage:
  python3 make_calendar.py 2026
  python3 make_calendar.py 2026 --out calendar_2026.pdf
"""

import argparse
import calendar
import datetime as dt
from dataclasses import dataclass

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- UK holidays (England/Wales) ---
try:
    import holidays  # pip install holidays
except Exception:
    holidays = None


@dataclass
class Style:
    page_size = landscape(A4)
    margin = 9 * mm
    header_h = 20 * mm
    footer_h = 4 * mm

    tasks_w = 55 * mm  # width of Tasks column

    # Typography
    font = "Helvetica"
    font_bold = "Helvetica-Bold"
    title_size = 16
    small_size = 7
    normal_size = 9
    holiday_size = 6.5

    # Lines
    border_w = 1.2
    grid_w = 0.8
    light_w = 0.5


def iso_week_label(d: dt.date) -> str:
    return f"w{d.isocalendar().week:02d}"


def month_name(year: int, month: int) -> str:
    return f"{calendar.month_name[month]} {year}"


def prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def set_grey(c: canvas.Canvas, v: float):
    c.setStrokeColor(colors.Color(v, v, v))
    c.setFillColor(colors.Color(v, v, v))


def draw_line(c: canvas.Canvas, x1, y1, x2, y2, lw=0.8):
    c.setLineWidth(lw)
    c.line(x1, y1, x2, y2)


def fill_rect(c: canvas.Canvas, x, y, w, h, grey: float):
    c.saveState()
    c.setFillColor(colors.Color(grey, grey, grey))
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.restoreState()


def draw_box_sides(c: canvas.Canvas, x, y, w, h, lw: float, left=True, right=True, top=True, bottom=True):
    c.setLineWidth(lw)
    if left:
        c.line(x, y, x, y + h)
    if right:
        c.line(x + w, y, x + w, y + h)
    if bottom:
        c.line(x, y, x + w, y)
    if top:
        c.line(x, y + h, x + w, y + h)


def build_uk_holidays(year: int) -> dict[dt.date, str]:
    if holidays is None:
        return {}
    # England subdivision provides the standard England/Wales bank holidays well enough for printing.
    uk = holidays.UnitedKingdom(years=year, subdiv="England")
    return {d: name for d, name in uk.items()}


def draw_mini_month(c: canvas.Canvas, year: int, month: int, x, y, w, h, firstweekday=calendar.MONDAY):
    """
    Draw a tiny month grid WITHOUT internal grid lines (numbers only + outer box).
    """
    cal = calendar.Calendar(firstweekday=firstweekday)
    weeks = cal.monthdatescalendar(year, month)

    # Outer box
    set_grey(c, 0.1)
    draw_box_sides(c, x, y, w, h, lw=0.6)

    # Title
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 2, y + h - 8, calendar.month_name[month])

    top = y + h - 10
    grid_h = h - 12
    rows = len(weeks) + 1  # weekday row
    cols = 7
    cell_w = w / cols
    cell_h = grid_h / rows

    # Weekday letters
    wd = ["M", "T", "W", "T", "F", "S", "S"]
    c.setFont("Helvetica", 5.5)
    set_grey(c, 0.15)
    for i, ch in enumerate(wd):
        c.drawCentredString(x + (i + 0.5) * cell_w, top - 0.8 * cell_h, ch)

    # Dates
    c.setFont("Helvetica", 5.2)
    for r, week in enumerate(weeks):
        for col, d in enumerate(week):
            yy = top - (r + 2) * cell_h + 1
            xx = x + col * cell_w
            if d.month != month:
                set_grey(c, 0.70)
            else:
                set_grey(c, 0.15)
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

    # Overall printable area
    page_x = m
    page_y = m
    page_w = W - 2 * m
    page_h = H - 2 * m

    # Header box
    header_x = page_x
    header_h = s.header_h
    header_y = page_y + page_h - header_h
    header_w = page_w

    # Below header: calendar + tasks area
    below_y = page_y + s.footer_h
    below_h = page_h - header_h - s.footer_h

    calendar_x = page_x
    calendar_y = below_y
    calendar_w = page_w - s.tasks_w
    calendar_h = below_h

    tasks_x = calendar_x + calendar_w
    tasks_y = below_y
    tasks_w = s.tasks_w
    tasks_h = below_h

    # --- Background fills (greyscale) ---
    fill_rect(c, header_x, header_y, header_w, header_h, 0.95)  # header band

    # Weekday header band inside calendar (light grey)
    weekday_row_ratio = 0.35
    cell_h_base = calendar_h / (6 + weekday_row_ratio)
    weekday_h = cell_h_base * weekday_row_ratio
    day_h = cell_h_base

    fill_rect(c, calendar_x, calendar_y + calendar_h - weekday_h, calendar_w, weekday_h, 0.92)

    # Tasks header band
    tasks_header_h = 16
    fill_rect(c, tasks_x, tasks_y + tasks_h - tasks_header_h, tasks_w, tasks_header_h, 0.92)

    # --- Boxes / compartments ---
    set_grey(c, 0.1)

    # Header box: full rectangle
    draw_box_sides(c, header_x, header_y, header_w, header_h, lw=s.border_w)

    # Calendar box: left/top/bottom (right edge shared with tasks via separator)
    draw_box_sides(c, calendar_x, calendar_y, calendar_w, calendar_h, lw=s.border_w, left=True, right=False, top=True, bottom=True)

    # Tasks box: right/top/bottom (left edge shared)
    draw_box_sides(c, tasks_x, tasks_y, tasks_w, tasks_h, lw=s.border_w, left=False, right=True, top=True, bottom=True)

    # Shared vertical separator line between calendar and tasks
    draw_line(c, tasks_x, calendar_y, tasks_x, calendar_y + calendar_h, lw=s.border_w)

    # --- Header content ---
    set_grey(c, 0.1)
    c.setFont(s.font_bold, s.title_size)
    c.drawString(header_x + 6, header_y + header_h - 16, month_name(year, month))

    # 3 mini months in header top-right
    mini_area_w = 90 * mm
    mini_area_h = 18 * mm
    mini_area_x = header_x + header_w - mini_area_w - 6
    mini_area_y = header_y + 2
    draw_three_mini_months(c, year, month, mini_area_x, mini_area_y, mini_area_w, mini_area_h)

    # --- Tasks header text + underline ---
    set_grey(c, 0.1)
    c.setFont(s.font_bold, 10)
    c.drawCentredString(tasks_x + tasks_w / 2, tasks_y + tasks_h - 12, "Tasks")
    draw_line(c, tasks_x, tasks_y + tasks_h - tasks_header_h, tasks_x + tasks_w, tasks_y + tasks_h - tasks_header_h, lw=s.grid_w)

    # --- Calendar grid ---
    cols = 7
    cell_w = calendar_w / cols

    # Weekday labels
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    c.setFont(s.font_bold, s.normal_size)
    weekday_text_y = calendar_y + calendar_h - (weekday_h / 2) - 3
    set_grey(c, 0.1)
    for col, name in enumerate(weekdays):
        cx = calendar_x + col * cell_w
        c.drawCentredString(cx + cell_w / 2, weekday_text_y, name)

    # Grid lines: vertical column lines
    set_grey(c, 0.35)
    for i in range(1, cols):  # internal column lines only (box + separator provide edges)
        x = calendar_x + i * cell_w
        draw_line(c, x, calendar_y, x, calendar_y + calendar_h, lw=s.grid_w)

    # Grid lines: day row separators
    # bottom border already drawn by box; draw internal horizontals only:
    for r in range(1, 6):  # internal week separators between the 6 week rows
        y = calendar_y + r * day_h
        draw_line(c, calendar_x, y, calendar_x + calendar_w, y, lw=s.grid_w)

    # line under weekday header (separates weekday band from week rows)
    y_weekday = calendar_y + 6 * day_h
    draw_line(c, calendar_x, y_weekday, calendar_x + calendar_w, y_weekday, lw=s.grid_w)

    # --- Dates + holidays + week number inside Monday cell ---
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal.monthdatescalendar(year, month)

    # Force 6 week rows
    while len(weeks) < 6:
        last_week = weeks[-1]
        next_start = last_week[-1] + dt.timedelta(days=1)
        weeks.append([next_start + dt.timedelta(days=i) for i in range(7)])

    for r, week in enumerate(weeks):
        wn = iso_week_label(week[0])  # Monday of that week

        # y0 = bottom of row r (0 is top week row just below weekday header)
        y0 = calendar_y + (5 - r) * day_h

        for col, d in enumerate(week):
            x0 = calendar_x + col * cell_w

            # Week number inside Monday cell (light grey, bottom-left)
            if col == 0:
                set_grey(c, 0.70)
                c.setFont(s.font, 6.5)
                c.drawString(x0 + 2, y0 + 2, wn)

            # Date number (top-left)
            if d.month != month:
                set_grey(c, 0.70)
            else:
                set_grey(c, 0.15)

            c.setFont(s.font, s.normal_size)
            c.drawString(x0 + 2, y0 + day_h - 12, str(d.day))

            # Holiday label (current-month days only)
            if d.month == month and d in uk_hols:
                set_grey(c, 0.05)
                c.setFont(s.font, s.holiday_size)
                name = str(uk_hols[d])

                # Simple wrap across up to 2 lines
                max_chars = 18
                lines = []
                while name:
                    lines.append(name[:max_chars])
                    name = name[max_chars:]
                    if len(lines) == 2:
                        break

                text_y = y0 + day_h - 22
                for ln in lines:
                    c.drawString(x0 + 2, text_y, ln)
                    text_y -= 7

    # Footer page number (bottom-right)
    set_grey(c, 0.4)
    c.setFont(s.font, 8)
    c.drawRightString(page_x + page_w - 6, page_y + 2, f"Page {page_num} of {total_pages}")


def build_pdf(year: int, out_path: str):
    s = Style()
    c = canvas.Canvas(out_path, pagesize=s.page_size)

    total_pages = 12
    for i, month in enumerate(range(1, 13), start=1):
        draw_month_page(c, year, month, page_num=i, total_pages=total_pages, s=s)
        c.showPage()

    c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int, help="Year to generate, e.g. 2026")
    ap.add_argument("--out", default=None, help="Output PDF path")
    args = ap.parse_args()

    out = args.out or f"calendar_{args.year}.pdf"
    build_pdf(args.year, out)
    print(f"Created: {out}")


if __name__ == "__main__":
    main()
