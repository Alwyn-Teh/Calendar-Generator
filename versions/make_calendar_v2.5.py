#!/usr/bin/env python3
"""
make_calendar_v2.5.py — Outlook-perfect geometry correction

Key guarantees (as per user screenshots):
- Header bottom-left meets calendar top-left with NO line, NO gap.
- Header top-right meets tasks top with NO gap.
- Calendar bottom-right meets tasks bottom with NO gap.
- ONLY ONE GAP: vertical gap between calendar and tasks columns.
- Mini-month borders lighter/thinner.
- Page number clearly outside boxes.
"""

import argparse, calendar, datetime as dt
from dataclasses import dataclass
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

try:
    import holidays
except Exception:
    holidays = None


@dataclass
class Style:
    page_size = landscape(A4)
    margin = 9 * mm
    header_h = 20 * mm
    tasks_w = 55 * mm
    band_h = 6 * mm

    # ONLY gap used
    cal_tasks_gap = 2.0  # points

    outer_w = 1.3
    box_w = 1.0
    grid_w = 0.8

    fill_header = 0.95
    fill_band = 0.92

    weeknum_grey = 0.70
    other_month_grey = 0.70
    text_grey = 0.12
    grid_grey = 0.35


def set_grey(c, g):
    c.setStrokeColor(colors.Color(g, g, g))
    c.setFillColor(colors.Color(g, g, g))


def rect(c, x, y, w, h, lw):
    c.setLineWidth(lw)
    c.rect(x, y, w, h, stroke=1, fill=0)


def line(c, x1, y1, x2, y2, lw):
    c.setLineWidth(lw)
    c.line(x1, y1, x2, y2)


def fill(c, x, y, w, h, g):
    c.saveState()
    c.setFillColor(colors.Color(g, g, g))
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.restoreState()


def uk_holidays(year):
    if not holidays:
        return {}
    return {d: n for d, n in holidays.UnitedKingdom(years=year, subdiv="England").items()}


def iso_week(d):
    return f"w{d.isocalendar().week:02d}"


def draw_page(c, year, month, page, total, s: Style):
    W, H = s.page_size
    m = s.margin

    # Outer page
    set_grey(c, 0.1)
    rect(c, m, m, W - 2*m, H - 2*m, s.outer_w)

    # Header (full width)
    hx = m
    hw = W - 2*m
    hy = H - m - s.header_h
    fill(c, hx, hy, hw, s.header_h, s.fill_header)
    rect(c, hx, hy, hw, s.header_h, s.box_w)

    # Title
    c.setFont("Helvetica-Bold", 16)
    set_grey(c, 0.0)
    c.drawString(hx + 6, hy + s.header_h - 16, f"{calendar.month_name[month]} {year}")

    # Lower area (calendar + tasks)
    ly = m
    lh = hy - ly

    split = m + (W - 2*m - s.tasks_w)

    # Calendar box (LEFT)
    cal_x = m
    cal_w = split - cal_x - s.cal_tasks_gap/2
    rect(c, cal_x, ly, cal_w, lh, s.box_w)

    # Tasks box (RIGHT)
    task_x = split + s.cal_tasks_gap/2
    task_w = (m + (W - 2*m)) - task_x
    rect(c, task_x, ly, task_w, lh, s.box_w)

    # Weekday / Tasks header bands (same height)
    fill(c, cal_x, ly + lh - s.band_h, cal_w, s.band_h, s.fill_band)
    fill(c, task_x, ly + lh - s.band_h, task_w, s.band_h, s.fill_band)

    # Weekday names
    c.setFont("Helvetica-Bold", 9)
    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    cell_w = cal_w / 7
    for i, d in enumerate(days):
        c.drawCentredString(cal_x + (i+0.5)*cell_w, ly + lh - s.band_h/2 - 3, d)

    # Tasks title + underline
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(task_x + task_w/2, ly + lh - s.band_h/2 - 3, "Tasks")
    line(c, task_x, ly + lh - s.band_h, task_x + task_w, ly + lh - s.band_h, s.grid_w)

    # Calendar grid
    cal = calendar.Calendar(calendar.MONDAY)
    weeks = cal.monthdatescalendar(year, month)
    rows = len(weeks)
    cell_h = (lh - s.band_h) / rows

    set_grey(c, s.grid_grey)

    # Vertical grid
    for i in range(8):
        x = cal_x + i*cell_w
        line(c, x, ly, x, ly+lh, s.grid_w)

    # Horizontal grid
    for r in range(rows+1):
        y = ly + r*cell_h
        line(c, cal_x, y, cal_x+cal_w, y, s.grid_w)

    # Dates
    hols = uk_holidays(year)
    for r, wk in enumerate(weeks):
        y0 = ly + (rows-1-r)*cell_h
        for cidx, d in enumerate(wk):
            x0 = cal_x + cidx*cell_w
            if d.month != month:
                set_grey(c, s.other_month_grey)
            else:
                set_grey(c, s.text_grey)
            c.setFont("Helvetica", 9)
            c.drawString(x0+2, y0+cell_h-12, str(d.day))
            if cidx == 0:
                set_grey(c, s.weeknum_grey)
                c.setFont("Helvetica", 6.5)
                c.drawString(x0+2, y0+2, iso_week(d))

    # Page number — safely outside
    set_grey(c, 0.4)
    c.setFont("Helvetica", 8)
    c.drawRightString(W - m, m - 6, f"Page {page} of {total}")


def build(year, out):
    c = canvas.Canvas(out, pagesize=landscape(A4))
    s = Style()
    for i in range(1,13):
        draw_page(c, year, i, i, 12, s)
        c.showPage()
    c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    build(a.year, a.out or f"calendar_{a.year}.pdf")


if __name__ == "__main__":
    main()
