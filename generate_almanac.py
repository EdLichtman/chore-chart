#!/usr/bin/env python3
"""Generate a yearly chore almanac from chores_almanac.yaml"""

import yaml
import re
import calendar
import subprocess
import json
import os
from datetime import date, timedelta
from collections import defaultdict

try:
    from docx import Document
    from docx.oxml import parse_xml, OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.shared import RGBColor, Pt, Inches, Emu
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


def convert_to_image(docx_file: str, output_dir: str) -> list:
    """Convert DOCX to PNG pages via Word COM (accurate rendering) + fitz. Returns list of PNG paths."""
    if not HAS_FITZ:
        raise ImportError("PyMuPDF (fitz) required. Install: py -m pip install pymupdf")

    import win32com.client
    docx_name = os.path.splitext(os.path.basename(docx_file))[0]
    pdf_path = os.path.join(output_dir, docx_name + ".pdf")
    abs_docx = os.path.abspath(docx_file)
    abs_pdf = os.path.abspath(pdf_path)

    # Use Word COM to export to PDF — Word-accurate rendering, not LibreOffice
    print(f"Converting {docx_file} to PDF via Word...")
    word = None
    doc = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(abs_docx)
        doc.ExportAsFixedFormat(abs_pdf, 17)  # 17 = wdExportFormatPDF
    finally:
        if doc:
            doc.Close(False)
        if word:
            word.Quit()

    if not os.path.exists(abs_pdf):
        raise FileNotFoundError(f"Word PDF export failed — expected {abs_pdf}")

    print("Rendering PDF pages to PNG (150 DPI)...")
    png_paths = []
    pdf_doc = fitz.open(abs_pdf)
    for page_num, page in enumerate(pdf_doc):
        pix = page.get_pixmap(dpi=150)
        png_path = os.path.join(output_dir, f"{docx_name}_page_{page_num + 1}.png")
        pix.save(png_path)
        png_paths.append(png_path)
    pdf_doc.close()

    print(f"Rendered {len(png_paths)} page(s).")
    return png_paths



MONTH_MAP = {name.lower(): i for i, name in enumerate(
    ['', 'January', 'February', 'March', 'April', 'May', 'June',
     'July', 'August', 'September', 'October', 'November', 'December']) if i > 0}
MONTH_MAP.update({k[:3]: v for k, v in MONTH_MAP.items()})


def week_anchor(d):
    """Snap to Mon–Thu's Monday or Fri–Sun's next Monday (mirrors Angular getWeekAnchor)."""
    mon_based = d.weekday()  # Mon=0 ... Sun=6
    if mon_based <= 3:
        return d - timedelta(days=mon_based)
    else:
        return d + timedelta(days=7 - mon_based)


def snap_date(d, day_pin, year):
    """Resolve a chore date to its display date.
    day_pin supersedes week_anchor: pin to that day of the month exactly.
    Without day_pin, apply week_anchor but clamp back-snapped dates to the anchor
    so occurrences never drift into the previous year."""
    if day_pin:
        return d.replace(day=int(day_pin))
    snapped = week_anchor(d)
    return snapped if snapped.year == year else d


def add_months(d, n):
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def parse_interval(s):
    """Parse interval string → (n, unit) matching the Angular Interval model."""
    s = s.strip().lower()
    if s == 'weekly':                    return (1, 'week')
    if s in ('bi-weekly', 'biweekly'):  return (2, 'week')
    if s == 'monthly':                   return (1, 'month')
    if s in ('1 year', 'annual', 'annually'): return (1, 'year')
    m = re.match(r'every\s+(\d+)\s+(day|week|month|year)s?$', s)
    if m:
        return (int(m.group(1)), m.group(2))
    return None


def parse_month_day(s):
    """Parse 'May 1' or 'Apr 15' → (month_int, day_int)"""
    parts = s.strip().split()
    if len(parts) == 2:
        month = MONTH_MAP.get(parts[0].lower())
        if month:
            return (month, int(parts[1]))
    return None


def parse_active_window(window_str, year):
    """Parse 'May 1 - June 1' → (start_date, end_date). Handles year wraparound."""
    parts = re.split(r'\s*[–-]\s*', window_str.strip(), maxsplit=1)
    if len(parts) != 2:
        return None, None
    start = parse_month_day(parts[0])
    end = parse_month_day(parts[1])
    if not start or not end:
        return None, None
    start_date = date(year, start[0], start[1])
    end_date = date(year, end[0], end[1])
    if end_date < start_date:
        end_date = date(year + 1, end[0], end[1])
    return start_date, end_date


def generate_occurrences(anchor, n, unit, end_date):
    """Yield dates from anchor through end_date at the given interval."""
    current = anchor
    while current <= end_date:
        yield current
        if unit == 'week':    current += timedelta(weeks=n)
        elif unit == 'day':   current += timedelta(days=n)
        elif unit == 'month': current = add_months(current, n)
        elif unit == 'year':  current = add_months(current, n * 12)


def get_season(d, year=None):
    """Return season name for a given date using astronomical boundaries.
    If year is not provided, infer it from the date."""
    if year is None:
        year = d.year

    # Check each season's date range
    for season in ['Winter', 'Spring', 'Summer', 'Fall']:
        start, end = get_season_date_range(season, year)
        if start <= d <= end:
            return season

    # Fallback: if date is in Dec 21-31 of current year, it's Winter of next year
    if d.month == 12 and d.day >= 21:
        return "Winter"

    # This shouldn't happen, but fallback to month-based logic
    month = d.month
    if month in (12, 1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Spring"
    elif month in (6, 7, 8):
        return "Summer"
    else:
        return "Fall"


def get_season_date_range(season, year):
    """Return (start_date, end_date) for a given season in the given year.
    Astronomical dates for 2026 and thereabouts."""
    if season == "Winter":
        # Dec 21 of previous year to Mar 19
        return (date(year - 1, 12, 21), date(year, 3, 19))
    elif season == "Spring":
        # Mar 20 to Jun 20
        return (date(year, 3, 20), date(year, 6, 20))
    elif season == "Summer":
        # Jun 21 to Sep 22
        return (date(year, 6, 21), date(year, 9, 22))
    else:  # Fall
        # Sep 23 to Dec 20
        return (date(year, 9, 23), date(year, 12, 20))


def expand_chore(chore, year):
    """Expand a chore into (parent_name, subchore_name, date, categories, details_list, is_subchore) tuples.

    For chores with subchores, returns one tuple per subchore occurrence.
    For regular chores, subchore_name is None and is_subchore is False.
    """
    rows = []
    name = chore['name']
    categories = chore.get('category', [])

    # Check if this chore has subchores
    subchores = chore.get('subchores', [])
    has_subchores = len(subchores) > 0

    def add_row(chore_date):
        if has_subchores:
            # Add parent row (with no subchore_name)
            rows.append((name, None, chore_date, categories, None, False))
            # Then add each subchore row
            for subchore in subchores:
                subchore_name = subchore['name']
                subchore_details = subchore.get('details', [])
                rows.append((name, subchore_name, chore_date, categories, subchore_details, True))
        else:
            details = chore.get('details', [])
            rows.append((name, None, chore_date, categories, details, False))

    if 'schedule' in chore:
        for entry in chore['schedule']:
            if entry.get('status') == 'inactive':
                continue
            freq = entry.get('frequency') or entry.get('interval')
            months_str = entry.get('months', '')
            if not freq or not months_str:
                continue
            interval = parse_interval(freq)
            if not interval:
                continue
            month_parts = re.split(r'\s*[-–]\s*', months_str.strip())
            if len(month_parts) != 2:
                continue
            start_m = MONTH_MAP.get(month_parts[0].strip().lower()[:3])
            end_m = MONTH_MAP.get(month_parts[1].strip().lower()[:3])
            if not start_m or not end_m:
                continue
            anchor = date(year, start_m, 1)
            end = date(year, end_m, calendar.monthrange(year, end_m)[1])
            for d in generate_occurrences(anchor, interval[0], interval[1], end):
                add_row(snap_date(d, chore.get('day_pin'), year))

    elif 'active_window' in chore:
        start, end = parse_active_window(chore['active_window'], year)
        if start and end:
            interval = parse_interval(chore.get('interval', '1 year'))
            if interval:
                anchor_day = chore.get('anchor_day')
                anchor = start.replace(day=anchor_day) if anchor_day else start
                for d in generate_occurrences(anchor, interval[0], interval[1], end):
                    add_row(snap_date(d, chore.get('day_pin'), year))

    elif 'starts' in chore:
        md = parse_month_day(chore['starts'])
        if md:
            interval = parse_interval(chore.get('interval', ''))
            if interval:
                anchor = date(year, md[0], md[1])
                for d in generate_occurrences(anchor, interval[0], interval[1], date(year, 12, 31)):
                    add_row(snap_date(d, chore.get('day_pin'), year))

    elif chore.get('interval', '').strip().lower() == 'seasonal':
        # One occurrence per season, anchored at the start of each season within the year.
        for season in ['Winter', 'Spring', 'Summer', 'Fall']:
            start, _ = get_season_date_range(season, year)
            add_row(max(start, date(year, 1, 1)))

    else:
        # interval-only: month_pin sets the cycle start month (default January)
        interval = parse_interval(chore.get('interval', ''))
        if interval:
            anchor_day = int(chore.get('anchor_day', 1))
            month_pin = int(chore['month_pin']) if chore.get('month_pin') else 1
            anchor = date(year, month_pin, anchor_day)
            for d in generate_occurrences(anchor, interval[0], interval[1], date(year, 12, 31)):
                add_row(snap_date(d, chore.get('day_pin'), year))

    return rows



def add_table_borders_to_docx(docx_file):
    """Add grid borders, header styling, and column widths to all tables in a DOCX file."""
    if not HAS_PYTHON_DOCX:
        print('Warning: python-docx not installed. Cannot add table styling.')
        print('Install with: py -m pip install python-docx')
        return False

    try:
        print(f'Adding table styling to {docx_file}...')
        doc = Document(docx_file)

        table_count = 0
        for table in doc.tables:
            tblPr = table._element.tblPr

            # Remove existing tblBorders if present
            for child in list(tblPr):
                if 'tblBorders' in child.tag:
                    tblPr.remove(child)

            # Create new borders element
            border_xml = (
                '<w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:top w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
                '<w:left w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
                '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
                '<w:right w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
                '<w:insideH w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
                '<w:insideV w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
                '</w:tblBorders>'
            )

            tblPr.append(parse_xml(border_xml))

            # Set table width to full page width
            table_width_xml = '<w:tblW xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:w="9400" w:type="dxa"/>'
            # Remove existing width if present
            for child in list(tblPr):
                if 'tblW' in child.tag:
                    tblPr.remove(child)
            tblPr.append(parse_xml(table_width_xml))

            # Style header row (first row) with grey background, bold text, center alignment
            if len(table.rows) > 0:
                header_row = table.rows[0]
                for cell_idx, cell in enumerate(header_row.cells):
                    tcPr = cell._element.get_or_add_tcPr()

                    # Add grey shading to header (slightly darker for better contrast)
                    shading_xml = '<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:fill="C0C0C0"/>'
                    tcPr.append(parse_xml(shading_xml))

                    # Vertical centering in header cell
                    vAlign_xml = '<w:vAlign xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="center"/>'
                    tcPr.append(parse_xml(vAlign_xml))

                    # Set column widths: Chore (2400), Category (1000), Predicted Date (1500), Actual (1600)
                    col_widths = [2400, 1000, 1500, 1600]
                    if cell_idx < len(col_widths):
                        width_xml = f'<w:tcW xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:w="{col_widths[cell_idx]}" w:type="dxa"/>'
                        # Remove existing width if present
                        for child in list(tcPr):
                            if 'tcW' in child.tag:
                                tcPr.remove(child)
                        tcPr.append(parse_xml(width_xml))

                    # Make header text bold, center-aligned, and dark yellow
                    for paragraph in cell.paragraphs:
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        for run in paragraph.runs:
                            run.font.bold = True
                            run.font.color.rgb = RGBColor(184, 134, 11)  # Dark yellow/goldenrod

                # Apply same column widths to data rows
                col_widths = [2400, 1000, 1500, 1600]
                for row in table.rows[1:]:
                    # Check if this is a subchore row (starts with spaces for indentation)
                    is_subchore = False
                    if len(row.cells) > 0:
                        first_cell_text = row.cells[0].text
                        is_subchore = first_cell_text.startswith('   ') or first_cell_text.startswith('\t')

                    for cell_idx, cell in enumerate(row.cells):
                        tcPr = cell._element.get_or_add_tcPr()

                        if cell_idx < len(col_widths):
                            width_xml = f'<w:tcW xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:w="{col_widths[cell_idx]}" w:type="dxa"/>'
                            # Remove existing width if present
                            for child in list(tcPr):
                                if 'tcW' in child.tag:
                                    tcPr.remove(child)
                            tcPr.append(parse_xml(width_xml))


            table_count += 1

        doc.save(docx_file)
        print(f'Added styling to {table_count} tables.')
        return True
    except Exception as e:
        print(f'Error adding table styling: {e}')
        return False



def load_chores(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        return yaml.safe_load(f)


def sort_dates_by_season(dates, season, year):
    """Sort dates in seasonal order (accounting for year boundaries)."""
    start_date, end_date = get_season_date_range(season, year)
    # Sort dates by their offset from the season start
    return sorted(dates, key=lambda d: (d - start_date).days)


def generate_markdown(chores_data, year, fix_flags=None):
    if fix_flags is None:
        fix_flags = {}
    lines = [
        f'# Chore Almanac {year}',
        f'*Generated: {date.today().strftime("%B %d, %Y")}*',
        '',
    ]

    # Build warning map for quick lookup
    warnings = {}
    for chore in chores_data.get('chores', []):
        if chore.get('warning'):
            warnings[chore['name']] = chore['warning']

    # Expand all chores
    all_rows = []
    for chore in chores_data.get('chores', []):
        all_rows += expand_chore(chore, year)

    # Deduplicate by (parent_name, subchore_name or name, date)
    seen = set()
    deduped = []
    for row in sorted(all_rows, key=lambda r: r[2]):  # sort by date (index 2)
        parent_name, subchore_name, d, categories, details, is_subchore = row
        key = (parent_name, subchore_name, d)
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    # Group by season, then by (parent_name, subchore_name)
    by_season = defaultdict(lambda: defaultdict(list))
    for parent_name, subchore_name, d, categories, details, is_subchore in deduped:
        season = get_season(d, year)
        group_key = (parent_name, subchore_name) if is_subchore else (parent_name, None)
        by_season[season][group_key].append((d, categories, details, is_subchore))

    # Season order for output
    season_order = ["Winter", "Spring", "Summer", "Fall"]
    lookahead_data = {entry.get('season'): entry.get('notes', [])
                      for entry in chores_data.get('lookahead', [])}

    next_season_map = {
        "Winter": "Spring",
        "Spring": "Summer",
        "Summer": "Fall",
        "Fall": "Winter"
    }

    for season in season_order:
        if season not in by_season:
            continue

        # Add page break before each season (except first)
        if lines and season != season_order[0]:
            lines.append('```{=openxml}')
            lines.append('<w:p>')
            lines.append('  <w:r>')
            lines.append('    <w:br w:type="page"/>')
            lines.append('  </w:r>')
            lines.append('</w:p>')
            lines.append('```')
            lines.append('')

        # Season header with date range
        start_date, end_date = get_season_date_range(season, year)
        date_range = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
        lines.append(f'## {season} ({date_range})')
        lines.append('')

        # Table rows - group by parent chore first
        chore_groups = defaultdict(list)
        for (parent_name, subchore_name), occurrences in by_season[season].items():
            dates_list = [d for d, _, _, _ in occurrences]
            sorted_dates = sort_dates_by_season(dates_list, season, year)

            if subchore_name is None:
                # Regular chore (no subchores)
                chore_groups[parent_name].append({
                    'is_parent': True,
                    'dates': sorted_dates,
                    'categories': occurrences[0][1],
                    'details': occurrences[0][2]
                })
            else:
                # Subchore - group under parent
                if parent_name not in chore_groups:
                    chore_groups[parent_name] = []
                # Find if parent exists, if not add it
                parent_entry = next((e for e in chore_groups[parent_name] if e.get('is_parent')), None)
                if not parent_entry:
                    # Add placeholder for parent (will fill details later)
                    chore_groups[parent_name].insert(0, {
                        'is_parent': True,
                        'dates': [],
                        'categories': occurrences[0][1],
                        'details': None
                    })
                # Add subchore entry
                chore_groups[parent_name].append({
                    'is_parent': False,
                    'subchore_name': subchore_name,
                    'dates': sorted_dates,
                    'categories': occurrences[0][1],
                    'details': occurrences[0][2]
                })

        if fix_flags.get("rule3_vertical_dates"):
            # Grid table: dates stacked vertically, one per line
            header_row = ["Chore", "Category", "Predicted Dates", "Actual"]
            col_widths = [30, 14, 20, 8]

            border = '+' + '+'.join(['-' * (w + 2) for w in col_widths]) + '+'
            sep    = '+' + '+'.join(['=' * (w + 2) for w in col_widths]) + '+'
            lines.append(border)
            lines.append('| ' + ' | '.join(h.ljust(w) for h, w in zip(header_row, col_widths)) + ' |')
            lines.append(sep)

            for parent_name in sorted(chore_groups.keys()):
                entries = chore_groups[parent_name]
                parent_entry = next((e for e in entries if e['is_parent']), None)
                subchore_entries = [e for e in entries if not e['is_parent']]

                if not parent_entry:
                    continue

                category_str = ', '.join(parent_entry['categories']) if parent_entry['categories'] else '?'
                dates_lines = [d.strftime('%b %d') for d in parent_entry['dates']] if parent_entry['dates'] else ['']
                name_col = parent_name
                if subchore_entries:
                    name_col += ''.join(f'/n ☐ {entry["subchore_name"]}' for entry in subchore_entries)

                max_lines = max(1, len(dates_lines))
                for line_i in range(max_lines):
                    n = name_col if line_i == 0 else ''
                    c = category_str if line_i == 0 else ''
                    d = dates_lines[line_i] if line_i < len(dates_lines) else ''
                    lines.append('| ' + ' | '.join([
                        n.ljust(col_widths[0]),
                        c.ljust(col_widths[1]),
                        d.ljust(col_widths[2]),
                        ''.ljust(col_widths[3]),
                    ]) + ' |')
                lines.append(border)
        else:
            # Pipe table (original format)
            lines.append('| Chore | Category | Predicted Dates | Actual |')
            lines.append('|-------|----------|-----------------|--------|')

            for parent_name in sorted(chore_groups.keys()):
                entries = chore_groups[parent_name]
                parent_entry = next((e for e in entries if e['is_parent']), None)
                subchore_entries = [e for e in entries if not e['is_parent']]

                if not parent_entry:
                    continue

                category_str = '/n'.join(parent_entry['categories']) if parent_entry['categories'] else '?'
                dates_str = '☐ ' + '/n☐ '.join([d.strftime('%b %d') for d in parent_entry['dates']]) if parent_entry['dates'] else ''
                if subchore_entries:
                    name_col = parent_name + ''.join(f'/n ☐ {entry["subchore_name"]}' for entry in subchore_entries)
                else:
                    name_col = parent_name

                lines.append(f'| {name_col} | {category_str} | {dates_str} | |')

        lines.append('')

        # Lookahead section
        next_season = next_season_map[season]
        lines.append(f'### Look Ahead to {next_season}:')
        if season in lookahead_data and lookahead_data[season]:
            for note in lookahead_data[season]:
                # Use underscore placeholder for empty notes
                content = note if note.strip() else '/n'
                lines.append(f'- {content}')
        else:
            # Add blank lines for user to fill in
            for _ in range(3):
                lines.append('- _____')
        lines.append('')

        # Details section with h4/h5 hierarchy
        lines.append(f'### {season} Details:')
        lines.append('')

        for parent_name in sorted(chore_groups.keys()):
            entries = chore_groups[parent_name]
            parent_has_details = any(e['is_parent'] and e.get('details') for e in entries)
            subchores_with_details = [e for e in entries if not e['is_parent'] and e.get('details')]

            if subchores_with_details:
                # If there are subchores, use h4 for parent
                lines.append(f'#### {parent_name}')
                if parent_name in warnings:
                    lines.append(f'> **⚠ Warning:** {warnings[parent_name]}')
                    lines.append('')  # Blank line after blockquote
                else:
                    lines.append('')
                for entry in subchores_with_details:
                    lines.append(f'- **{entry["subchore_name"]}**')
                    for detail in entry['details']:
                        lines.append(f'    - ☐ {detail}')
                lines.append('')
            elif parent_has_details:
                # No subchores, just parent with details
                for entry in entries:
                    if entry['is_parent'] and entry.get('details'):
                        lines.append(f'#### {parent_name}')
                        if parent_name in warnings:
                            lines.append(f'> **⚠ Warning:** {warnings[parent_name]}')
                            lines.append('')  # Blank line after blockquote
                        for detail in entry['details']:
                            lines.append(f'- ☐ {detail}')
                        lines.append('')

        lines.append('')

    return '\n'.join(lines)


def generate_purchase_schedule(chores_data):
    """Generate markdown for purchase schedule section."""
    purchase_schedule = chores_data.get('purchase_schedule', [])
    if not purchase_schedule:
        return ''

    lines = [
        '```{=openxml}',
        '<w:p>',
        '  <w:r>',
        '    <w:br w:type="page"/>',
        '  </w:r>',
        '</w:p>',
        '```',
        '',
        '## Purchase Schedule',
        '',
        '| Item | Buy Frequency | Notes |',
        '|------|---------------|-------|',
    ]

    for item in purchase_schedule:
        name = item.get('name', '')
        frequency = item.get('frequency', '')
        notes = item.get('notes', '')
        lines.append(f'| {name} | {frequency} | {notes} | |')

    lines.append('')
    return '\n'.join(lines)


def generate_as_needed(chores_data):
    """Generate markdown for as-needed/observable chores section."""
    as_needed = chores_data.get('as_needed_chores', [])
    if not as_needed:
        return ''

    lines = [
        '```{=openxml}',
        '<w:p>',
        '  <w:r>',
        '    <w:br w:type="page"/>',
        '  </w:r>',
        '</w:p>',
        '```',
        '',
        '## As-Needed Chores',
        '',
        '| Chore | Last Done | Notes |',
        '|-------|-----------|-------|',
    ]

    for chore in as_needed:
        name = chore.get('name', '')
        subchores = chore.get('subchores', [])
        cell_text = name + ''.join(f'/n ☐ {sc["name"]}' for sc in subchores)
        lines.append(f'| {cell_text} | | |')

    lines.append('')
    return '\n'.join(lines)



def fix_list_spacing(docx_file):
    """Reduce spacing between list items and detail paragraphs."""
    if not HAS_PYTHON_DOCX:
        return False

    try:
        print(f'Fixing list spacing in {docx_file}...')
        doc = Document(docx_file)

        ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

        # Zero out spacing on any paragraph that has a list numbering element (w:numPr)
        for para in doc.paragraphs:
            pPr = para._element.find(f'{{{ns}}}pPr')
            if pPr is None:
                continue
            if pPr.find(f'{{{ns}}}numPr') is None:
                continue
            existing = pPr.find(f'{{{ns}}}spacing')
            if existing is not None:
                existing.set(qn('w:after'), '0')
                existing.set(qn('w:before'), '0')
            else:
                spacing = OxmlElement('w:spacing')
                spacing.set(qn('w:after'), '0')
                spacing.set(qn('w:before'), '0')
                pPr.append(spacing)

        doc.save(docx_file)
        print('Fixed list spacing.')
        return True
    except Exception as e:
        print(f'Error fixing list spacing: {e}')
        return False


def add_yellow_bg_to_blockquotes(docx_file: str) -> bool:
    """Add yellow background shading to blockquote-style paragraphs."""
    if not HAS_PYTHON_DOCX:
        return False
    try:
        print(f"Adding yellow background to blockquotes in {docx_file}...")
        doc = Document(docx_file)
        shading_xml = (
            '<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ' w:val="clear" w:color="auto" w:fill="B8860B"/>'
        )
        count = 0
        for para in doc.paragraphs:
            style_name = para.style.name if para.style else ""
            if "Quote" in style_name or (para.text and para.text.startswith("⚠")):
                pPr = para._element.get_or_add_pPr()
                for child in list(pPr):
                    if "shd" in child.tag:
                        pPr.remove(child)
                pPr.append(parse_xml(shading_xml))
                count += 1
        doc.save(docx_file)
        print(f"  Applied yellow background to {count} paragraph(s).")
        return True
    except Exception as e:
        print(f"Error adding yellow background: {e}")
        return False


def remove_paragraph_borders(docx_file: str) -> bool:
    """Remove all paragraph border elements (pBdr) that create horizontal rules."""
    if not HAS_PYTHON_DOCX:
        return False
    try:
        print(f"Removing paragraph borders from {docx_file}...")
        doc = Document(docx_file)
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        count = 0
        for para in doc.paragraphs:
            pPr = para._element.find(f"{{{ns}}}pPr")
            if pPr is None:
                continue
            for child in list(pPr):
                if child.tag == f"{{{ns}}}pBdr":
                    pPr.remove(child)
                    count += 1
        doc.save(docx_file)
        print(f"  Removed {count} paragraph border element(s).")
        return True
    except Exception as e:
        print(f"Error removing paragraph borders: {e}")
        return False


def remove_empty_pages(docx_file: str) -> bool:
    """Remove empty paragraphs that create blank pages."""
    if not HAS_PYTHON_DOCX:
        return False
    try:
        print(f"Removing empty pages from {docx_file}...")
        doc = Document(docx_file)
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        removed = 0
        prev_had_page_break = False
        body = doc.element.body
        paras = list(body.iterchildren(f"{{{ns}}}p"))
        for para in paras:
            text = "".join(t.text or "" for t in para.iter(f"{{{ns}}}t")).strip()
            has_page_break = para.find(f".//{{{ns}}}br[@{{{ns}}}type='page']") is not None

            if prev_had_page_break and not text and not has_page_break:
                body.remove(para)
                removed += 1
            else:
                prev_had_page_break = has_page_break

        doc.save(docx_file)
        print(f"  Removed {removed} empty paragraph(s).")
        return True
    except Exception as e:
        print(f"Error removing empty pages: {e}")
        return False



def replace_newline_literals_in_docx(docx_file: str) -> bool:
    """Replace literal /n with actual line breaks in paragraphs and table cells."""
    if not HAS_PYTHON_DOCX:
        return False
    try:
        print(f"Replacing /n with newlines in {docx_file}...")
        doc = Document(docx_file)
        
        def process_paragraph(para):
            """Process a paragraph to replace /n with line breaks."""
            count = 0
            # Collect all text content first
            full_text = para.text
            if '/n' not in full_text:
                return count
            
            # Split by /n
            parts = full_text.split('/n')
            
            # Clear the paragraph
            para.clear()
            
            # Add parts back with line breaks between them
            for i, part in enumerate(parts):
                if i > 0:
                    # Add a line break before this part
                    run = para.add_run()
                    br = OxmlElement('w:br')
                    run._r.append(br)
                    count += 1
                
                if part:  # Only add run if there's text
                    para.add_run(part)
            
            return count
        
        # Process all paragraphs in the document
        replaced_count = 0
        for para in doc.paragraphs:
            replaced_count += process_paragraph(para)
        
        # Process paragraphs in table cells
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        replaced_count += process_paragraph(para)
        
        if replaced_count > 0:
            doc.save(docx_file)
            print(f"  Replaced {replaced_count} /n occurrence(s) with line breaks.")
        
        return True
    except Exception as e:
        print(f"Error replacing newline literals: {e}")
        return False


def _insert_field(para, field_instr: str):
    """Append a Word field to a paragraph."""
    run_begin = para.add_run()
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    run_begin._r.append(fld_begin)
    run_instr = para.add_run()
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = field_instr
    run_instr._r.append(instr)
    run_end = para.add_run()
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    run_end._r.append(fld_end)


def add_page_number_footer(docx_file: str) -> bool:
    """Add footer: season name (STYLEREF Heading 2) on left, page number on right."""
    if not HAS_PYTHON_DOCX:
        return False
    try:
        print(f"Adding footer to {docx_file}...")
        doc = Document(docx_file)
        for section in doc.sections:
            footer = section.footer
            para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            para.clear()
            try:
                para.style = doc.styles['Footer']
            except KeyError:
                pass
            _insert_field(para, ' STYLEREF "Heading 2" ')
            para.add_run('\t\t')
            _insert_field(para, ' PAGE ')
        doc.save(docx_file)
        print("  Footer added.")
        return True
    except Exception as e:
        print(f"  Footer error: {e}")
        return False


def post_process_docx(docx_file: str) -> None:
    """Run all post-processing steps on the DOCX file."""
    add_table_borders_to_docx(docx_file)
    replace_newline_literals_in_docx(docx_file)
    fix_list_spacing(docx_file)
    remove_empty_pages(docx_file)
    add_yellow_bg_to_blockquotes(docx_file)
    remove_paragraph_borders(docx_file)
    add_page_number_footer(docx_file)


# ============================================================================
# Direct DOCX generation (replaces pandoc pipeline)
# ============================================================================

def _add_page_break(doc):
    """Insert a hard page break."""
    p = doc.add_paragraph()
    r = p.add_run()
    br = OxmlElement('w:br')
    br.set(qn('w:type'), 'page')
    r._r.append(br)


def _set_cell_shading(cell, fill_color):
    """Apply a fill color (hex string like 'FFEB3B') to a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn('w:shd')):
        tcPr.remove(existing)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_color)
    tcPr.append(shd)


def _set_cell_width(cell, inches):
    """Set cell width in inches (converts to twips)."""
    tcPr = cell._tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn('w:tcW')):
        tcPr.remove(existing)
    tcW = OxmlElement('w:tcW')
    tcW.set(qn('w:w'), str(int(inches * 1440)))
    tcW.set(qn('w:type'), 'dxa')
    tcPr.append(tcW)


def _add_page_number_field(paragraph):
    """Append a Word PAGE field to the paragraph."""
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = 'PAGE'
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    run_begin = paragraph.add_run()
    run_begin._r.append(fld_begin)
    run_instr = paragraph.add_run()
    run_instr._r.append(instr)
    run_end = paragraph.add_run()
    run_end._r.append(fld_end)


def _setup_page_header(doc):
    """Set the document header with section name (left) and page number (right)."""
    section = doc.sections[0]
    header = section.header
    para = header.paragraphs[0]
    para.text = ''
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    # Use existing Header style which has built-in tab stops at center and right
    try:
        para.style = doc.styles['Header']
    except KeyError:
        pass
    para.add_run('Chore Almanac')
    para.add_run('\t\t')
    _add_page_number_field(para)


def _style_table_header(row, headers):
    """Style the header row: gray shading, bold dark-yellow centered text."""
    for cell, text in zip(row.cells, headers):
        _set_cell_shading(cell, 'C0C0C0')
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.text = ''
        run = p.add_run(text)
        run.font.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(184, 134, 11)


def _add_warning_paragraph(doc, warning_text):
    """Add a warning paragraph with yellow background highlighting."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(f'⚠ Warning: {warning_text}')
    run.font.bold = True
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


def _build_chore_groups(by_season, season, year):
    """Group occurrences by parent chore. Returns dict of parent_name -> list of entries."""
    chore_groups = defaultdict(list)
    for (parent_name, subchore_name), occurrences in by_season[season].items():
        dates_list = [d for d, _, _, _ in occurrences]
        sorted_dates = sort_dates_by_season(dates_list, season, year)

        if subchore_name is None:
            chore_groups[parent_name].append({
                'is_parent': True,
                'dates': sorted_dates,
                'categories': occurrences[0][1],
                'details': occurrences[0][2],
            })
        else:
            if parent_name not in chore_groups:
                chore_groups[parent_name] = []
            parent_entry = next((e for e in chore_groups[parent_name] if e.get('is_parent')), None)
            if not parent_entry:
                chore_groups[parent_name].insert(0, {
                    'is_parent': True,
                    'dates': [],
                    'categories': occurrences[0][1],
                    'details': None,
                })
            chore_groups[parent_name].append({
                'is_parent': False,
                'subchore_name': subchore_name,
                'dates': sorted_dates,
                'categories': occurrences[0][1],
                'details': occurrences[0][2],
            })
    return chore_groups


def _build_season_table(doc, chore_groups):
    """Build a 4-column chore table with stacked subchores under parent in same row."""
    # Start with just header row; add data rows dynamically
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    col_inches = [2.5, 0.9, 1.8, 1.0]
    
    # Style header row
    header_cells = table.rows[0].cells
    for cell, w in zip(header_cells, col_inches):
        _set_cell_width(cell, w)
    _style_table_header(table.rows[0], ['Chore', 'Category', 'Predicted Dates', 'Actual'])

    # Add data rows dynamically
    for parent_name in sorted(chore_groups.keys()):
        entries = chore_groups[parent_name]
        
        # Find parent and subchore entries
        parent_entry = next((e for e in entries if e['is_parent']), None)
        subchore_entries = [e for e in entries if not e['is_parent']]
        
        if not parent_entry:
            continue
        
        # Add a new row for this parent
        row = table.add_row()
        for cell, w in zip(row.cells, col_inches):
            _set_cell_width(cell, w)

        # Col 1: Name - parent + stacked subchores with /n separator
        name_cell = row.cells[0]
        name_p = name_cell.paragraphs[0]
        name_p.text = ''
        
        # Add parent name (bold)
        run = name_p.add_run(parent_name)
        run.font.bold = True
        
        # Add subchores as text with /n[] separator
        for subchore_entry in subchore_entries:
            name_p.add_run(f'/n[] {subchore_entry["subchore_name"]}')

        # Col 2: Category - stack with /n separator
        cat_cell = row.cells[1]
        cat_p = cat_cell.paragraphs[0]
        cat_p.text = ''
        cat_p.add_run('/n'.join(parent_entry['categories']) if parent_entry['categories'] else '?')

        # Col 3: Predicted Dates — one paragraph per date with ☐ checkbox
        dates_cell = row.cells[2]
        dates_cell.paragraphs[0].text = ''
        if parent_entry['dates']:
            for i, d in enumerate(parent_entry['dates']):
                p = dates_cell.paragraphs[0] if i == 0 else dates_cell.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.space_before = Pt(0)
                p.add_run(f'☐ {d.strftime("%b %d")}')

        # Col 4: Actual — leave empty

    return table


def build_docx(data, year, output_path):
    """Build the chore almanac DOCX directly with python-docx (no pandoc).

    Generates correct output by default — no fix_flags needed.
    """
    if not HAS_PYTHON_DOCX:
        raise ImportError("python-docx required. Install: py -m pip install python-docx")

    doc = Document()
    _setup_page_header(doc)

    # Title
    title = doc.add_heading(f'Chore Almanac {year}', level=1)
    subtitle = doc.add_paragraph()
    sub_run = subtitle.add_run(f'Generated: {date.today().strftime("%B %d, %Y")}')
    sub_run.italic = True

    # Build warning map
    warnings = {chore['name']: chore['warning']
                for chore in data.get('chores', [])
                if chore.get('warning')}

    # Expand and dedupe occurrences
    all_rows = []
    for chore in data.get('chores', []):
        all_rows += expand_chore(chore, year)

    seen = set()
    deduped = []
    for row in sorted(all_rows, key=lambda r: r[2]):
        parent_name, subchore_name, d, categories, details, is_subchore = row
        key = (parent_name, subchore_name, d)
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    by_season = defaultdict(lambda: defaultdict(list))
    for parent_name, subchore_name, d, categories, details, is_subchore in deduped:
        season = get_season(d, year)
        group_key = (parent_name, subchore_name) if is_subchore else (parent_name, None)
        by_season[season][group_key].append((d, categories, details, is_subchore))

    season_order = ['Winter', 'Spring', 'Summer', 'Fall']
    next_season_map = {'Winter': 'Spring', 'Spring': 'Summer', 'Summer': 'Fall', 'Fall': 'Winter'}
    lookahead_data = {entry.get('season'): entry.get('notes', [])
                      for entry in data.get('lookahead', [])}

    seasons_present = [s for s in season_order if s in by_season]
    for season_idx, season in enumerate(seasons_present):
        if season_idx > 0:
            _add_page_break(doc)

        # Season heading with date range
        start_date, end_date = get_season_date_range(season, year)
        date_range = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
        doc.add_heading(f'{season} ({date_range})', level=2)

        chore_groups = _build_chore_groups(by_season, season, year)

        # Table
        _build_season_table(doc, chore_groups)

        # Look Ahead
        doc.add_heading(f'Look Ahead to {next_season_map[season]}:', level=3)
        notes = lookahead_data.get(season, [])
        if notes:
            for note in notes:
                p = doc.add_paragraph(style='List Bullet')
                p.add_run(note if note.strip() else '_____')
        else:
            for _ in range(3):
                p = doc.add_paragraph(style='List Bullet')
                p.add_run('_____')

        # Details section
        doc.add_heading(f'{season} Details:', level=2)

        for parent_name in sorted(chore_groups.keys()):
            entries = chore_groups[parent_name]
            parent_has_details = any(e['is_parent'] and e.get('details') for e in entries)
            subchores_with_details = [e for e in entries if not e['is_parent'] and e.get('details')]

            if subchores_with_details:
                doc.add_heading(parent_name, level=4)
                if parent_name in warnings:
                    _add_warning_paragraph(doc, warnings[parent_name])
                for entry in subchores_with_details:
                    # Subchore heading: bullet + non-italic, indented
                    sp = doc.add_paragraph()
                    sp.paragraph_format.left_indent = Inches(0.25)
                    sp.paragraph_format.space_before = Pt(6)
                    sp.paragraph_format.space_after = Pt(2)
                    bullet_run = sp.add_run('• ')
                    bullet_run.font.bold = True
                    bullet_run.font.italic = False
                    bullet_run.font.size = Pt(12)
                    name_run = sp.add_run(entry['subchore_name'])
                    name_run.font.bold = True
                    name_run.font.italic = False
                    name_run.font.size = Pt(12)
                    for detail in entry['details']:
                        dp = doc.add_paragraph()
                        dp.paragraph_format.left_indent = Inches(0.5)
                        dp.paragraph_format.space_after = Pt(0)
                        dp.add_run(f'☐ {detail}')
            elif parent_has_details:
                for entry in entries:
                    if entry['is_parent'] and entry.get('details'):
                        doc.add_heading(parent_name, level=4)
                        if parent_name in warnings:
                            _add_warning_paragraph(doc, warnings[parent_name])
                        for detail in entry['details']:
                            dp = doc.add_paragraph()
                            dp.paragraph_format.left_indent = Inches(0.25)
                            dp.paragraph_format.space_after = Pt(0)
                            dp.add_run(f'☐ {detail}')

    # As-Needed Chores page
    if data.get('as_needed_chores'):
        _add_page_break(doc)
        doc.add_heading('As-Needed Chores', level=2)
        items = data['as_needed_chores']
        an_table = doc.add_table(rows=len(items) + 1, cols=3)
        an_table.style = 'Table Grid'
        an_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        an_widths = [3.0, 1.5, 2.5]
        for r in an_table.rows:
            for c, w in zip(r.cells, an_widths):
                _set_cell_width(c, w)
        _style_table_header(an_table.rows[0], ['Chore', 'Last Done', 'Notes'])
        for i, chore in enumerate(items):
            an_table.rows[i + 1].cells[0].text = chore.get('name', '')

    # Purchase Schedule page
    if data.get('purchase_schedule'):
        _add_page_break(doc)
        doc.add_heading('Purchase Schedule', level=2)
        items = data['purchase_schedule']
        ps_table = doc.add_table(rows=len(items) + 1, cols=4)
        ps_table.style = 'Table Grid'
        ps_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        ps_widths = [2.0, 1.5, 2.5, 1.0]
        for r in ps_table.rows:
            for c, w in zip(r.cells, ps_widths):
                _set_cell_width(c, w)
        _style_table_header(ps_table.rows[0], ['Item', 'Buy Frequency', 'Notes', 'Stocked?'])
        for i, item in enumerate(items):
            row = ps_table.rows[i + 1]
            row.cells[0].text = item.get('name', '')
            row.cells[1].text = item.get('frequency', '')
            row.cells[2].text = item.get('notes', '')

    doc.save(output_path)
    print(f'Built DOCX directly: {output_path}')


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    yaml_file   = r'c:\Users\elich\OneDrive\Eddie\Chores\chores_almanac.yaml'
    output_docx = r'c:\Users\elich\OneDrive\Eddie\Chores\chore_almanac.docx'
    output_dir  = r'c:\Users\elich\OneDrive\Eddie\Chores\debug'
    output_md   = r'c:\Users\elich\OneDrive\Eddie\Chores\chore_almanac.md'
    template    = r'c:\Users\elich\OneDrive\Eddie\Chores\TABLE_TEMPLATE.docx'

    print(f'Loading {yaml_file}...')
    data = load_chores(yaml_file)

    print('Generating almanac markdown...')
    md = generate_markdown(data, year=2026)
    md += generate_purchase_schedule(data)
    md += generate_as_needed(data)

    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(md)

    print('Converting to DOCX with pandoc...')
    try:
        pandoc_cmd = ['pandoc', output_md, '-f', 'markdown', '-t', 'docx',
                      '-o', output_docx, '--reference-doc', template, '--standalone']
        subprocess.run(pandoc_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f'Error running pandoc: {e}')
        return
    except FileNotFoundError:
        print('Error: pandoc not found. Install from https://pandoc.org/installing.html')
        return

    post_process_docx(output_docx)

    try:
        convert_to_image(output_docx, output_dir)
    except Exception as e:
        print(f'Image conversion failed: {e}')

    print('Done.')


if __name__ == '__main__':
    main()
