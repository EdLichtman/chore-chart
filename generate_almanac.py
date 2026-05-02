#!/usr/bin/env python3
"""Generate a yearly chore almanac from chores_almanac.yaml"""

import yaml
import re
import calendar
import subprocess
import os
from datetime import date, timedelta
from collections import defaultdict

try:
    from docx import Document
    from docx.oxml import parse_xml
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import RGBColor
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

def all_rules_pass(results: dict) -> bool:
    return all(r["status"] != "FAIL" for r in results.get("rules", []))


LIBREOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


def find_libreoffice() -> str:
    for path in LIBREOFFICE_PATHS:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "LibreOffice not found. Install from https://www.libreoffice.org/ "
        "or via: choco install libreoffice"
    )


def convert_to_image(docx_file: str, output_dir: str) -> list:
    """Convert DOCX to PNG pages via LibreOffice + fitz. Returns list of PNG paths."""
    if not HAS_FITZ:
        raise ImportError("PyMuPDF (fitz) required. Install: py -m pip install pymupdf")

    soffice = find_libreoffice()
    docx_name = os.path.splitext(os.path.basename(docx_file))[0]
    pdf_path = os.path.join(output_dir, docx_name + ".pdf")

    print(f"Converting {docx_file} to PDF via LibreOffice...")
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", output_dir, docx_file],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice DOCX->PDF failed:\n{result.stderr}")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Expected PDF at {pdf_path} but it was not created")

    print("Rendering PDF pages to PNG (150 DPI)...")
    png_paths = []
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        png_path = os.path.join(output_dir, f"{docx_name}_page_{page_num + 1}.png")
        pix.save(png_path)
        png_paths.append(png_path)
    doc.close()

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


def add_page_headers(docx_file):
    """Placeholder: page headers disabled due to parse_xml corruption risk.

    Field codes (STYLEREF, PAGE) require complex XML that parse_xml() cannot
    reliably construct. Word's XML parser is strict and rejects malformed headers.

    Future approach: add headers via pandoc Lua filter or modify TABLE_TEMPLATE.docx
    before pandoc runs."""
    pass


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


def generate_grid_table(headers, rows):
    """Generate a proper pandoc grid table."""
    # Column widths: Chore, Category, Predicted Date, Actual Date
    col_widths = [25, 12, 18, 6]

    lines = []

    # Top border
    border = '+' + '+'.join(['-' * w for w in col_widths]) + '+'
    lines.append(border)

    # Header row
    header_cells = []
    for h, w in zip(headers, col_widths):
        header_cells.append(h.ljust(w))
    lines.append('| ' + ' | '.join(header_cells) + ' |')

    # Header separator
    sep = '+' + '+'.join(['=' * w for w in col_widths]) + '+'
    lines.append(sep)

    # Data rows
    for row in rows:
        row_cells = []
        for cell, w in zip(row, col_widths):
            cell_str = str(cell) if cell else ''
            row_cells.append(cell_str.ljust(w))
        lines.append('| ' + ' | '.join(row_cells) + ' |')
        lines.append(border)

    return '\n'.join(lines)


def generate_grid_table_enhanced(rows, col_widths):
    """Generate a pandoc grid table with support for multi-line cells."""
    lines = []

    def split_cell_lines(cell):
        """Split cell content by newlines."""
        return str(cell).split('\n') if cell else ['']

    def pad_cell(text, width):
        """Pad text to width."""
        return text.ljust(width)

    # Top border
    border = '+' + '+'.join(['-' * w for w in col_widths]) + '+'
    lines.append(border)

    # Process each row
    for row in rows:
        # Split each cell by newlines to handle multi-line content
        cell_lines = [split_cell_lines(cell) for cell in row]
        max_lines = max(len(lines) for lines in cell_lines) if cell_lines else 1

        # Output each line of the row
        for line_idx in range(max_lines):
            row_parts = []
            for cell_idx, cell_line_list in enumerate(cell_lines):
                if line_idx < len(cell_line_list):
                    text = cell_line_list[line_idx]
                else:
                    text = ''
                row_parts.append(pad_cell(text, col_widths[cell_idx]))
            lines.append('| ' + ' | '.join(row_parts) + ' |')

        # Row border
        lines.append(border)

    return lines


def load_chores(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        return yaml.safe_load(f)


def sort_dates_by_season(dates, season, year):
    """Sort dates in seasonal order (accounting for year boundaries)."""
    start_date, end_date = get_season_date_range(season, year)
    # Sort dates by their offset from the season start
    return sorted(dates, key=lambda d: (d - start_date).days)


def generate_markdown(chores_data, year):
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

        # Pipe table with multi-line cell support
        lines.append('| Chore | Category | Predicted Dates | Actual |')
        lines.append('|-------|----------|-----------------|--------|')

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

        # Output table rows
        for parent_name in sorted(chore_groups.keys()):
            entries = chore_groups[parent_name]
            for idx, entry in enumerate(entries):
                if entry['is_parent']:
                    # Parent row
                    category_str = ', '.join(entry['categories']) if entry['categories'] else '?'
                    dates_str = ' / '.join([d.strftime('%b %d') for d in entry['dates']]) if entry['dates'] else ''
                    lines.append(f'| {parent_name} | {category_str} | {dates_str} | |')
                else:
                    # Subchore row with em-space indentation (no bullet)
                    dates_str = ' / '.join([d.strftime('%b %d') for d in entry['dates']])
                    lines.append(f'|   {entry["subchore_name"]} | | {dates_str} | |')

        # Add 3 blank rows
        for _ in range(3):
            lines.append('| | | | |')

        lines.append('')

        # Lookahead section
        next_season = next_season_map[season]
        lines.append(f'### Look Ahead to {next_season}:')
        if season in lookahead_data and lookahead_data[season]:
            for note in lookahead_data[season]:
                # Use underscore placeholder for empty notes
                content = note if note.strip() else "_____"
                lines.append(f'- {content}')
        else:
            # Add blank lines for user to fill in
            for _ in range(3):
                lines.append('- _____')
        lines.append('')

        # Details section with h4/h5 hierarchy
        lines.append(f'## {season} Details:')
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
                    lines.append(f'##### {entry["subchore_name"]}')
                    for detail in entry['details']:
                        lines.append(f'    - [ ] {detail}')  # Indent 4 spaces for sub-list
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
                            lines.append(f'- [ ] {detail}')
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
        '| Item | Buy Frequency | Notes | Stocked? |',
        '|------|---------------|-------|----------|',
    ]

    for item in purchase_schedule:
        name = item.get('name', '')
        frequency = item.get('frequency', '')
        notes = item.get('notes', '')
        lines.append(f'| {name} | {frequency} | {notes} | |')

    # Add blank rows for user to fill in
    for _ in range(3):
        lines.append('| | | | |')

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
        lines.append(f'| {name} | | |')

    # Add blank rows
    for _ in range(5):
        lines.append('| | | |')

    lines.append('')
    return '\n'.join(lines)


def fix_subchore_heading_style(docx_file):
    """Remove italic from Heading 5 style and add left indent."""
    if not HAS_PYTHON_DOCX:
        return False

    try:
        print(f'Fixing subchore heading style in {docx_file}...')
        doc = Document(docx_file)

        # Access Heading 5 style
        styles = doc.styles
        heading5_style = None
        for style in styles:
            if style.name == 'Heading 5':
                heading5_style = style
                break

        if heading5_style:
            # Remove italic
            heading5_style.font.italic = False
            # Add left indent (720 twips = 0.5 inch)
            heading5_style.paragraph_format.left_indent = 457200  # in EMUs (914400 EMU = 1 inch)

        doc.save(docx_file)
        print('Fixed subchore heading style.')
        return True
    except Exception as e:
        print(f'Error fixing subchore heading style: {e}')
        return False


def fix_list_spacing(docx_file):
    """Reduce spacing between list items."""
    if not HAS_PYTHON_DOCX:
        return False

    try:
        print(f'Fixing list spacing in {docx_file}...')
        doc = Document(docx_file)

        # Find and modify List Paragraph style
        styles = doc.styles
        for style in styles:
            try:
                if style.name == 'List Paragraph' and hasattr(style, 'paragraph_format'):
                    style.paragraph_format.space_after = 0
            except AttributeError:
                pass

        doc.save(docx_file)
        print('Fixed list spacing.')
        return True
    except Exception as e:
        print(f'Error fixing list spacing: {e}')
        return False


def main():
    yaml_file = r'c:\Users\elich\OneDrive\Eddie\Chores\chores_almanac.yaml'
    output_md = r'c:\Users\elich\OneDrive\Eddie\Chores\chore_almanac.md'
    output_docx = r'c:\Users\elich\OneDrive\Eddie\Chores\chore_almanac.docx'

    print(f'Loading {yaml_file}...')
    data = load_chores(yaml_file)

    print('Generating almanac markdown...')
    md = generate_markdown(data, year=2026)

    # Add purchase schedule and as-needed sections
    md += generate_purchase_schedule(data)
    md += generate_as_needed(data)

    print(f'Writing {output_md}...')
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(md)

    # Convert markdown to docx using pandoc with table template
    print(f'Converting to docx with pandoc...')
    try:
        template_file = r'c:\Users\elich\OneDrive\Eddie\Chores\TABLE_TEMPLATE.docx'
        pandoc_cmd = [
            'pandoc',
            output_md,
            '-f', 'markdown',
            '-t', 'docx',
            '-o', output_docx,
            '--reference-doc', template_file,
            '--standalone'
        ]
        subprocess.run(pandoc_cmd, check=True)
        print(f'Successfully created {output_docx}')
    except subprocess.CalledProcessError as e:
        print(f'Error running pandoc: {e}')
        print('Note: Make sure pandoc is installed and in your PATH')
    except FileNotFoundError:
        print('Error: pandoc not found. Install pandoc from https://pandoc.org/installing.html')

    # Post-process DOCX
    add_table_borders_to_docx(output_docx)
    # add_page_headers(output_docx)  # DISABLED - diagnose corruption
    # fix_subchore_heading_style(output_docx)  # DISABLED - diagnose corruption
    # fix_list_spacing(output_docx)  # DISABLED - diagnose corruption

    # Clean up intermediate markdown file
    if os.path.exists(output_md):
        os.remove(output_md)
        print(f'Cleaned up {output_md}')

    # Run verification tests
    print()
    print('Running verification tests...')
    try:
        import subprocess as sp
        result = sp.run(['py', 'verify_headers.py'], capture_output=True, text=True, cwd=os.path.dirname(output_docx) or '.')
        print(result.stdout)
        if result.returncode != 0:
            print('WARNING: Header verification failed!')
    except Exception as e:
        print(f'Note: Could not run verification tests ({e})')

    print('Done!')


if __name__ == '__main__':
    main()
