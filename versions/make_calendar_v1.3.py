#!/usr/bin/env python3
"""
make_calendar.py — Generate an Outlook-ish printable calendar PDF:
- A4 landscape
- 1 month per page
- Monday-first
- ISO week numbers in a left strip
- Tasks column on the right with ruled lines
- 3 mini months in header (prev/current/next) top-right
- UK public holidays (England/Wales) rendered into day cells (no syncing)

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

    # Layout proportions
    weeknum_w = 10 * mm
    tasks_w = 55 * mm  # adjust if you want wider/narrower task column

    # Typography
    font = "Helvetica"
    font_bold = "Helvetica-Bold"

    title_size = 16
    small_size = 7
    normal_size = 9
    holiday_size = 6.5  # text inside cells

    # Line widths
    border_w = 1.2
    grid_w = 0.8
    light_w = 0.5


def iso_week_label(d: dt.date) -> str:
    return f"w{d.isocalendar().week:02d}"


def month_name(year: int, month: int) -> str:
    return f"{calendar.month_name[month]} {year}"


def prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def draw_rect(c: canvas.Canvas, x, y, w, h, lw=1.0):
    c.setLineWidth(lw)
    c.rect(x, y, w, h, stroke=1, fill=0)


def draw_line(c: canvas.Canvas, x1, y1, x2, y2, lw=0.8):
    c.setLineWidth(lw)
    c.line(x1, y1, x2, y2)


def set_grey(c: canvas.Canvas, v: float):
    c.setStrokeColor(colors.Color(v, v, v))
    c.setFillColor(colors.Color(v, v, v))


def build_uk_holidays(year: int):
    """
    Returns dict[date] -> holiday name for England/Wales.
    If holidays package isn't available, returns empty dict.
    """
    if holidays is None:
        return {}
    uk = holidays.UnitedKingdom(years=year, subdiv="England")  # "England" covers Eng/Wales bank hols well
    # Convert to plain dict with datetime.date keys
    return {d: name for d, name in uk.items()}


def draw_mini_month(c: canvas.Canvas, year: int, month: int, x, y, w, h, firstweekday=calendar.MONDAY):
    """
    Draw a tiny month grid.
    """
    cal = calendar.Calendar(firstweekday=firstweekday)
    weeks = cal.monthdatescalendar(year, month)

    # Outer box
    set_grey(c, 0.1)
    draw_rect(c, x, y, w, h, lw=0.6)

    # Title
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 2, y + h - 8, calendar.month_name[month])

    # Grid area
    top = y + h - 10
    grid_h = h - 12
    rows = len(weeks) + 1  # + weekday row
    cols = 7
    cell_w = w / cols
    cell_h = grid_h / rows

    # Weekday letters
    wd = ["M", "T", "W", "T", "F", "S", "S"]
    c.setFont("Helvetica", 5.5)
    for i, ch in enumerate(wd):
        c.drawCentredString(x + (i + 0.5) * cell_w, top - 0.8 * cell_h, ch)

    # Dates
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
    """
    Draw prev/current/next mini months in a single right-hand header area.
    """
    py, pm = prev_month(year, month)
    ny, nm = next_month(year, month)

    gap = 2 * mm
    mini_w = (w - 2 * gap) / 3.0
    mini_h = h

    draw_mini_month(c, py, pm, x, y, mini_w, mini_h)
    draw_mini_month(c, year, month, x + mini_w + gap, y, mini_w, mini_h)
    draw_mini_month(c, ny, nm, x + 2 * (mini_w + gap), y, mini_w, mini_h)


def draw_month_page(c: canvas.Canvas, year: int, month: int, page_num: int, total_pages: int, s: Style):
    W, H = s.page_size
    m = s.margin

    # Holidays for this year (used for current month days)
    uk_hols = build_uk_holidays(year)

    # Regions
    content_x = m
    content_y = m + s.footer_h
    content_w = W - 2 * m
    content_h = H - 2 * m - s.header_h - s.footer_h

    header_x = m
    header_y = H - m - s.header_h
    header_w = content_w
    header_h = s.header_h

    # Outer border around header+content
    set_grey(c, 0.1)
    draw_rect(c, m, m, content_w, H - 2 * m, lw=s.border_w)

    # Header separator line
    draw_line(c, m, header_y, m + header_w, header_y, lw=s.border_w)

    # Header text
    c.setFont(s.font_bold, s.title_size)
    c.drawString(header_x + 6, header_y + header_h - 16, month_name(year, month))

    # Three mini months in header top-right
    mini_area_w = 90 * mm  # enough for 3 minis on A4 landscape
    mini_area_h = 18 * mm
    mini_area_x = header_x + header_w - mini_area_w - 6
    mini_area_y = header_y + 2
    draw_three_mini_months(c, year, month, mini_area_x, mini_area_y, mini_area_w, mini_area_h)

    # Layout inside content: weeknums strip + main grid + tasks column
    weeknum_w = s.weeknum_w
    tasks_w = s.tasks_w
    grid_x = content_x + weeknum_w
    grid_y = content_y
    grid_w = content_w - weeknum_w - tasks_w
    grid_h = content_h

    tasks_x = grid_x + grid_w
    tasks_y = content_y
    tasks_h = content_h

    # Draw vertical separators
    draw_line(c, content_x + weeknum_w, content_y, content_x + weeknum_w, content_y + content_h, lw=s.border_w)
    draw_line(c, tasks_x, tasks_y, tasks_x, tasks_y + tasks_h, lw=s.border_w)

    # Tasks header
    set_grey(c, 0.1)
    c.setFont(s.font_bold, 10)
    c.drawCentredString(tasks_x + tasks_w / 2, tasks_y + tasks_h - 12, "Tasks")
    draw_line(c, tasks_x, tasks_y + tasks_h - 16, tasks_x + tasks_w, tasks_y + tasks_h - 16, lw=s.grid_w)

    # Calendar grid
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal.monthdatescalendar(year, month)

    # Force 6 week rows for consistent Outlook look
    while len(weeks) < 6:
        last_week = weeks[-1]
        next_start = last_week[-1] + dt.timedelta(days=1)
        weeks.append([next_start + dt.timedelta(days=i) for i in range(7)])

    weekday_row_ratio = 0.6
    cols = 7

    cell_w = grid_w / cols
    cell_h_base = grid_h / (6 + weekday_row_ratio)   # base unit
    weekday_h = cell_h_base * weekday_row_ratio
    day_h = cell_h_base

    cell_w = grid_w / cols
    cell_h = grid_h / rows
    weekday_h = cell_h * weekday_row_ratio
    day_h = cell_h

    # Weekday headings row
    set_grey(c, 0.1)
    c.setFont(s.font_bold, s.normal_size)
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for col, name in enumerate(weekdays):
        cx = grid_x + col * cell_w
        c.drawCentredString(cx + cell_w / 2,
                            grid_y + grid_h - weekday_h * 0.7,
                            name)

    # Horizontal line under weekday row
    draw_line(c,
              grid_x,
              grid_y + grid_h - weekday_h,
              grid_x + grid_w,
              grid_y + grid_h - weekday_h,
              lw=s.grid_w)

    # Grid lines (main)
    set_grey(c, 0.35)

    # Vertical lines (7 columns)
    for i in range(cols + 1):
        draw_line(c, grid_x + i * cell_w, grid_y, grid_x + i * cell_w, grid_y + grid_h, lw=s.grid_w)

    # Horizontal lines:
    # bottom border
    draw_line(c, grid_x, grid_y, grid_x + grid_w, grid_y, lw=s.grid_w)

    # 6 week-row separators + top border (using day_h)
    for r in range(1, 7):  # 1..6
        y = grid_y + r * day_h
        draw_line(c, grid_x, y, grid_x + grid_w, y, lw=s.grid_w)

    # line under weekday header
    y_weekday = grid_y + 6 * day_h
    draw_line(c, grid_x, y_weekday, grid_x + grid_w, y_weekday, lw=s.grid_w)

    # top border
    draw_line(c, grid_x, grid_y + grid_h, grid_x + grid_w, grid_y + grid_h, lw=s.grid_w)

    # Week number strip lines
    set_grey(c, 0.35)
    draw_line(c, content_x, grid_y + 6 * day_h, content_x + weeknum_w, grid_y + 6 * day_h, lw=s.grid_w)
    for r in range(6):
        y = grid_y + grid_h - weekday_h - (r + 1) * day_h
        draw_line(c, content_x, y, content_x + weeknum_w, y, lw=s.grid_w)

    # Week number labels + date numbers + holidays
    for r, week in enumerate(weeks):
        monday = week[0]
        set_grey(c, 0.2)
        c.setFont(s.font, s.small_size)
        wn = iso_week_label(monday)
        wn_y = grid_y + grid_h - weekday_h - (r + 1) * day_h + 2
        c.drawString(content_x + 2, wn_y, wn)

        for col, d in enumerate(week):
            x0 = grid_x + col * cell_w
            y0 = grid_y + grid_h - weekday_h - (r + 1) * day_h # bottom of that cell row

            # Date number (top-left of cell)
            if d.month != month:
                set_grey(c, 0.70)
            else:
                set_grey(c, 0.15)
            c.setFont(s.font, s.normal_size)
            c.drawString(x0 + 2, y0 + day_h - 12, str(d.day))

            # Holiday label (current-month days only, to avoid clutter)
            if d.month == month and d in uk_hols:
                set_grey(c, 0.05)
                c.setFont(s.font, s.holiday_size)

                # Wrap very simply across up to 2 lines
                name = str(uk_hols[d])
                max_chars = 18  # tuned for A4 cell width
                lines = []
                while name:
                    lines.append(name[:max_chars])
                    name = name[max_chars:]
                    if len(lines) == 2:
                        break

                # Place under the date number
                text_y = y0 + day_h - 22
                for ln in lines:
                    c.drawString(x0 + 2, text_y, ln)
                    text_y -= 7

    # Footer page number (bottom-right)
    set_grey(c, 0.4)
    c.setFont(s.font, 8)
    c.drawRightString(W - m - 6, m + 4, f"Page {page_num} of {total_pages}")


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

