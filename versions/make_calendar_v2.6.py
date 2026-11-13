#!/usr/bin/env python3
"""
make_calendar_v2.5.py — Outlook-style printable calendar PDF (A4 landscape)

Goals (per Alwyn’s “Outlook-perfect” requirements):
- Three separate compartments (Header / Month grid / Tasks) with *visible gaps* where they meet,
  creating an “apparent double-line” look WITHOUT thicker strokes.
- NO vertical split/gap inside the header box (header is one continuous box).
- Month grid uses 5 week rows when possible, but automatically uses 6 when the month needs it.
- Weekday band (Mon..Sun) height == Tasks header ("Tasks") height.
- Mini months (prev/current/next) appear in header top-right; their borders are thin/greyscale to reduce clutter.
- Page number is OUTSIDE the compartment boxes (in the bottom margin area inside outer page border),
  so it never gets crossed by compartment borders.

Usage:
  python3 make_calendar_v2.5.py 2026 --out calendar_2026.pdf
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

    # Outer border margin
    margin = 9 * mm

    # Inside outer border, keep a little padding so compartment borders don't sit on top of the outer border
    inner_pad = 2.0 * mm

    # Reserve a bottom band (inside outer border) for the page number (NOT part of compartments)
    page_num_band_h = 6.0 * mm

    # Header box height
    header_h = 20.0 * mm

    # Tasks column width
    tasks_w = 55.0 * mm

    # Weekday band height (also tasks header band)
    band_h = 6.0 * mm

    # Gaps (white space) between compartment boxes to create "double line" illusion
    gap_h = 2.0 * mm  # between header and lower boxes
    gap_v = 1.4 * mm  # between month grid and tasks column

    # Typography
    font = "Helvetica"
    font_bold = "Helvetica-Bold"
    title_size = 16
    weekday_size = 9
    date_size = 9
    weeknum_size = 6.5
    holiday_size = 6.5

    # Line widths / greys
    outer_w = 1.3
    box_w = 1.0
    grid_w = 0.8
    mini_w = 0.4

    fill_header = 0.95
    fill_band = 0.92

    text_grey = 0.05
    grid_grey = 0.35
    other_month_grey = 0.70
    weeknum_grey = 0.72
    mini_grey = 0.45


def grey(v: float):
    return colors.Color(v, v, v)


def set_stroke(c: canvas.Canvas, v: float, lw: float):
    c.setStrokeColor(grey(v))
    c.setLineWidth(lw)


def set_fill(c: canvas.Canvas, v: float):
    c.setFillColor(grey(v))


def draw_rect(c: canvas.Canvas, x, y, w, h, lw: float, stroke_grey: float):
    c.saveState()
    set_stroke(c, stroke_grey, lw)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.restoreState()


def fill_rect(c: canvas.Canvas, x, y, w, h, fill_grey: float):
    c.saveState()
    set_fill(c, fill_grey)
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.restoreState()


def build_uk_holidays(year: int):
    if holidays is None:
        return {}
    uk = holidays.UnitedKingdom(years=year, subdiv="England")
    return {d: str(name) for d, name in uk.items()}


def prev_month(year: int, month: int):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def next_month(year: int, month: int):
    return (year + 1, 1) if month == 12 else (year, month + 1)


def iso_week_label(d: dt.date) -> str:
    return f"w{d.isocalendar().week:02d}"


def month_weeks(year: int, month: int):
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    return cal.monthdatescalendar(year, month)  # list[list[date]] length is 4–6


def draw_mini_month(c: canvas.Canvas, year: int, month: int, x, y, w, h, s: Style):
    weeks = month_weeks(year, month)
    # Outer only (no internal grid)
    draw_rect(c, x, y, w, h, lw=s.mini_w, stroke_grey=s.mini_grey)

    c.setFont(s.font, 6.4)
    c.setFillColor(grey(0.10))
    c.drawString(x + 2, y + h - 8, calendar.month_name[month])

    # Tiny content (weekday letters + dates), no lines
    wd = ["M", "T", "W", "T", "F", "S", "S"]
    top = y + h - 10
    grid_h = h - 12
    rows = len(weeks) + 1
    cell_w = w / 7.0
    cell_h = grid_h / rows

    c.setFont(s.font, 5.4)
    for i, ch in enumerate(wd):
        c.setFillColor(grey(0.10))
        c.drawCentredString(x + (i + 0.5) * cell_w, top - 0.80 * cell_h, ch)

    c.setFont(s.font, 5.1)
    for r, week in enumerate(weeks):
        for col, d in enumerate(week):
            yy = top - (r + 2) * cell_h + 1
            xx = x + col * cell_w
            c.setFillColor(grey(s.other_month_grey if d.month != month else 0.10))
            c.drawRightString(xx + cell_w - 1.2, yy, str(d.day))


def draw_three_mini_months(c: canvas.Canvas, year: int, month: int, x, y, w, h, s: Style):
    py, pm = prev_month(year, month)
    ny, nm = next_month(year, month)
    gap = 2.0 * mm
    mini_w = (w - 2 * gap) / 3.0
    draw_mini_month(c, py, pm, x, y, mini_w, h, s)
    draw_mini_month(c, year, month, x + mini_w + gap, y, mini_w, h, s)
    draw_mini_month(c, ny, nm, x + 2 * (mini_w + gap), y, mini_w, h, s)


def draw_month_page(c: canvas.Canvas, year: int, month: int, page_num: int, total_pages: int, s: Style):
    W, H = s.page_size
    m = s.margin

    # Outer border
    draw_rect(c, m, m, W - 2*m, H - 2*m, lw=s.outer_w, stroke_grey=0.10)

    # Inner content bounds (so compartment borders don't overdraw the outer border)
    ix = m + s.inner_pad
    iy = m + s.inner_pad
    iW = (W - 2*m) - 2*s.inner_pad
    iH = (H - 2*m) - 2*s.inner_pad

    # Bottom band for page number (inside outer border)
    page_band_h = s.page_num_band_h
    content_bottom = iy + page_band_h
    content_top = iy + iH

    # Header box (single continuous)
    header_h = s.header_h
    header_y = content_top - header_h
    header_x = ix
    header_w = iW

    fill_rect(c, header_x, header_y, header_w, header_h, s.fill_header)
    draw_rect(c, header_x, header_y, header_w, header_h, lw=s.box_w, stroke_grey=0.10)

    # Lower boxes sit below header, separated by vertical GAP (no lines in the gap)
    lower_top = header_y - s.gap_h
    lower_y = content_bottom
    lower_h = lower_top - lower_y

    # Split month/tasks with vertical GAP
    split_x = ix + (iW - s.tasks_w)
    cal_x = ix
    cal_y = lower_y
    cal_w = (split_x - s.gap_v/2) - cal_x
    cal_h = lower_h

    tasks_x = split_x + s.gap_v/2
    tasks_y = lower_y
    tasks_w = (ix + iW) - tasks_x
    tasks_h = lower_h

    # Calendar + Tasks boxes
    draw_rect(c, cal_x, cal_y, cal_w, cal_h, lw=s.box_w, stroke_grey=0.10)
    draw_rect(c, tasks_x, tasks_y, tasks_w, tasks_h, lw=s.box_w, stroke_grey=0.10)

    # Bands (weekday row + tasks header), equal height
    band_h = s.band_h
    fill_rect(c, cal_x, cal_y + cal_h - band_h, cal_w, band_h, s.fill_band)
    fill_rect(c, tasks_x, tasks_y + tasks_h - band_h, tasks_w, band_h, s.fill_band)

    # Band bottom border (same weight/grey as grid)
    set_stroke(c, s.grid_grey, s.grid_w)
    c.line(cal_x, cal_y + cal_h - band_h, cal_x + cal_w, cal_y + cal_h - band_h)
    c.line(tasks_x, tasks_y + tasks_h - band_h, tasks_x + tasks_w, tasks_y + tasks_h - band_h)

    # Title
    c.setFont(s.font_bold, s.title_size)
    c.setFillColor(grey(0.0))
    c.drawString(header_x + 6, header_y + header_h - 16, f"{calendar.month_name[month]} {year}")

    # Mini months in header (top-right)
    mini_area_w = 90 * mm
    mini_area_h = 18 * mm
    mini_x = header_x + header_w - mini_area_w - 6
    mini_y = header_y + 2
    draw_three_mini_months(c, year, month, mini_x, mini_y, mini_area_w, mini_area_h, s)

    # Weekday labels
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    c.setFont(s.font_bold, s.weekday_size)
    c.setFillColor(grey(0.0))

    col_w = cal_w / 7.0
    band_y = cal_y + cal_h - band_h
    for i, name in enumerate(weekdays):
        cx = cal_x + i * col_w
        c.drawCentredString(cx + col_w/2, band_y + (band_h - s.weekday_size)/2 - 1, name)

    # Tasks header
    c.setFont(s.font_bold, s.weekday_size)
    c.drawCentredString(tasks_x + tasks_w/2, tasks_y + tasks_h - band_h + (band_h - s.weekday_size)/2 - 1, "Tasks")

    # Month grid below weekday band
    weeks = month_weeks(year, month)
    rows = len(weeks)  # 4..6 (we accommodate 5 or 6 automatically)
    grid_top = band_y
    grid_h = grid_top - cal_y
    row_h = grid_h / rows

    # Vertical grid lines
    set_stroke(c, s.grid_grey, s.grid_w)
    for i in range(1, 7):
        x = cal_x + i * col_w
        c.line(x, cal_y, x, grid_top)

    # Horizontal grid lines
    for r in range(1, rows):
        y = cal_y + r * row_h
        c.line(cal_x, y, cal_x + cal_w, y)

    # Dates + week numbers
    uk_hols = build_uk_holidays(year)
    c.setFont(s.font, s.date_size)

    for r, week in enumerate(weeks):
        for col, d in enumerate(week):
            cell_x = cal_x + col * col_w
            cell_y = grid_top - (r + 1) * row_h

            # Date number (top-left-ish)
            if d.month != month:
                c.setFillColor(grey(s.other_month_grey))
            else:
                c.setFillColor(grey(0.0))
            c.drawString(cell_x + 2, cell_y + row_h - 12, str(d.day))

            # Week number label (in Monday cell only, light grey, near left of cell)
            if col == 0:
                c.setFont(s.font, s.weeknum_size)
                c.setFillColor(grey(s.weeknum_grey))
                c.drawString(cell_x + 2, cell_y + row_h - 24, iso_week_label(d))
                c.setFont(s.font, s.date_size)

            # UK holiday label (small, below date)
            if d in uk_hols and d.month == month:
                c.setFont(s.font, s.holiday_size)
                c.setFillColor(grey(0.0))
                name = uk_hols[d]
                c.drawString(cell_x + 2, cell_y + row_h - 22, name[:22])
                c.setFont(s.font, s.date_size)

    # Page number in bottom band (outside compartment boxes)
    c.setFont(s.font, 9)
    c.setFillColor(grey(0.15))
    c.drawRightString(ix + iW, iy + 2.0, f"Page {page_num} of {total_pages}")


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


if __name__ == "__main__":
    main()
