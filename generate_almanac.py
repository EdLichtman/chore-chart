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


def validate_image(image_paths: list, checklist_path: str) -> dict:
    """Call claude -p to validate image pages against checklist. Returns parsed JSON."""
    checklist = open(checklist_path, encoding="utf-8").read()

    paths_str = "\n".join(f"- {p}" for p in image_paths)
    prompt = (
        checklist
        + "\n\n---\n"
        + "Read each of these image files using the Read tool and inspect them against each rule above:\n"
        + paths_str
        + "\n\nFor each rule, output a JSON object. Output ONLY valid JSON, no markdown fences, no prose:\n"
        + '{\n  "rules": [\n    {"id": 1, "name": "...", "status": "PASS" | "FAIL" | "UNCERTAIN", "reason": "..."}\n  ]\n}'
    )

    result = subprocess.run(
        ["claude", "-p", prompt,
         "--allowedTools", "Read",
         "--output-format", "json",
         "--no-session-persistence"],
        capture_output=True, text=True, encoding="utf-8",
        timeout=180, stdin=subprocess.DEVNULL
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude validation failed (exit {result.returncode}):\n{result.stderr}")

    envelope = json.loads(result.stdout)
    raw = envelope.get("result", "")

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(raw)


def write_report(results: dict, attempt: int, max_attempts: int,
                 fix_log: list, output_file: str) -> None:
    from datetime import datetime
    lines = [
        "ALMANAC VALIDATION REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Attempt: {attempt} of {max_attempts}",
        "",
        "RULE RESULTS:",
    ]

    status_sym = {"PASS": "✓", "FAIL": "✗", "UNCERTAIN": "⚠"}
    passing = failing = uncertain = 0
    for rule in results.get("rules", []):
        sym = status_sym.get(rule["status"], "?")
        name = rule.get("name", "")
        reason = rule.get("reason", "")
        lines.append(f"  {sym} Rule {rule['id']} — {name:<45} {rule['status']:<10} ({reason})")
        if rule["status"] == "PASS": passing += 1
        elif rule["status"] == "FAIL": failing += 1
        else: uncertain += 1

    lines += ["", f"PASSING: {passing}  FAILING: {failing}  UNCERTAIN: {uncertain}"]

    if fix_log:
        lines += ["", "FIXES APPLIED:"]
        for entry in fix_log:
            lines.append(f"  Attempt {entry['attempt']}:")
            for fix in entry.get("fixes_applied", []):
                lines.append(f"    Rule {fix['rule']}: {fix['action']}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Report written to {output_file}")


_RULE_FIX_MAP = {
    3:  ("rule3_vertical_dates",  "Stack dates vertically with newline separator; switch to grid table"),
    4:  ("rule4_yellow_bg",       "Add yellow background shading to blockquote paragraphs"),
    5:  ("rule5_no_separators",   "Remove paragraph borders between sections"),
    6:  ("rule6_no_empty_rows",   "Remove empty table rows from generated markdown"),
    8:  ("rule8_no_empty_pages",  "Delete empty pages via python-docx"),
    9:  ("rule9_page_headers",    "Add page headers via LibreOffice macro"),
    13: ("rule13_bullet_nonitalic", "Prepend bullet to subchore names; remove italic"),
}


def attempt_fixes(results: dict, fix_flags: dict, fix_log: list, attempt: int) -> None:
    """Set fix flags for all failing rules and record what was attempted."""
    failing = [r for r in results.get("rules", []) if r["status"] == "FAIL"]
    if not failing:
        return

    fixes_applied = []
    for rule in failing:
        rule_id = rule["id"]
        if rule_id not in _RULE_FIX_MAP:
            print(f"  No fix defined for Rule {rule_id} — skipping")
            continue
        flag_name, description = _RULE_FIX_MAP[rule_id]
        fix_flags[flag_name] = True
        fixes_applied.append({"rule": rule_id, "action": description})
        print(f"  Queued fix for Rule {rule_id}: {description}")

    fix_log.append({"attempt": attempt, "rules_attempted": [r["id"] for r in failing],
                    "fixes_applied": fixes_applied})


def escalate_to_user(results: dict, fix_log: list, report_file: str) -> None:
    """Print escalation summary and record user response in the report."""
    print()
    print("=" * 50)
    print("VALIDATION FAILED AFTER 3 ATTEMPTS")
    print("=" * 50)
    print()
    print("Current rule status:")
    for r in results.get("rules", []):
        sym = {"PASS": "✓", "FAIL": "✗", "UNCERTAIN": "⚠"}.get(r["status"], "?")
        print(f"  {sym} {r['status']}: Rule {r['id']} — {r['name']}")
    print()
    print("Fix attempts made:")
    for entry in fix_log:
        actions = ", ".join(f"Rule {f['rule']}: {f['action']}" for f in entry["fixes_applied"])
        print(f"  Attempt {entry['attempt']}: {actions}")
    print()
    print("Possible next steps:")
    print("  A) Try a different LibreOffice approach")
    print("  B) Try rebuilding DOCX from scratch with python-docx only (no pandoc)")
    print("  C) Try docx2pdf + manual post-processing")
    print(f"  D) Review the document manually — run: start {os.path.dirname(report_file)}\\chore_almanac.docx")
    print()

    user_response = input("Would you like to try a different approach? (A/B/C/D or describe): ").strip()

    with open(report_file, "a", encoding="utf-8") as f:
        f.write(f"\nUser response: {user_response}\n")

    print(f"Response recorded in {report_file}")


DEFAULT_FIX_FLAGS = {
    "rule3_vertical_dates": False,
    "rule4_yellow_bg": False,
    "rule5_no_separators": False,
    "rule6_no_empty_rows": False,
    "rule8_no_empty_pages": False,
    "rule9_page_headers": False,
    "rule13_bullet_nonitalic": False,
}

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

            border = '+' + '+'.join(['-' * w for w in col_widths]) + '+'
            sep    = '+' + '+'.join(['=' * w for w in col_widths]) + '+'
            lines.append(border)
            lines.append('| ' + ' | '.join(h.ljust(w) for h, w in zip(header_row, col_widths)) + ' |')
            lines.append(sep)

            for parent_name in sorted(chore_groups.keys()):
                entries = chore_groups[parent_name]
                for entry in entries:
                    if entry['is_parent']:
                        category_str = ', '.join(entry['categories']) if entry['categories'] else '?'
                        dates_lines = [d.strftime('%b %d') for d in entry['dates']] if entry['dates'] else ['']
                        name_col = parent_name
                    else:
                        category_str = ''
                        dates_lines = [d.strftime('%b %d') for d in entry['dates']]
                        prefix = "• " if fix_flags.get("rule13_bullet_nonitalic") else "  "
                        name_col = f"{prefix}{entry['subchore_name']}"

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
                for idx, entry in enumerate(entries):
                    if entry['is_parent']:
                        category_str = ', '.join(entry['categories']) if entry['categories'] else '?'
                        dates_str = ' / '.join([d.strftime('%b %d') for d in entry['dates']]) if entry['dates'] else ''
                        lines.append(f'| {parent_name} | {category_str} | {dates_str} | |')
                    else:
                        dates_str = ' / '.join([d.strftime('%b %d') for d in entry['dates']])
                        lines.append(f'|   {entry["subchore_name"]} | | {dates_str} | |')

            if not fix_flags.get("rule6_no_empty_rows"):
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


def add_page_headers_libreoffice(docx_file: str) -> bool:
    """Attempt to add page headers via LibreOffice Basic macro. Best-effort — may not work."""
    try:
        import tempfile
        soffice = find_libreoffice()

        macro_src = (
            "import uno\n"
            "\n"
            "def AddHeaders():\n"
            "    ctx = uno.getComponentContext()\n"
            "    smgr = ctx.ServiceManager\n"
            "    desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)\n"
            "    url = uno.systemPathToFileUrl(r'" + docx_file.replace("\\", "\\\\") + "')\n"
            "    doc = desktop.loadComponentFromURL(url, '_blank', 0, ())\n"
            "    page_styles = doc.StyleFamilies.getByName('PageStyles')\n"
            "    default_style = page_styles.getByName('Default Page Style')\n"
            "    default_style.HeaderIsOn = True\n"
            "    default_style.HeaderIsShared = True\n"
            "    header_text = default_style.HeaderText\n"
            "    cursor = header_text.createTextCursor()\n"
            "    cursor.gotoStart(False)\n"
            "    cursor.gotoEnd(True)\n"
            "    header_text.insertString(cursor, 'Chore Almanac', False)\n"
            "    doc.store()\n"
            "    doc.close(True)\n"
            "\n"
            "AddHeaders()\n"
        )

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                         encoding="utf-8", delete=False) as f:
            f.write(macro_src)
            macro_path = f.name

        result = subprocess.run(
            [soffice, "--headless", "--norestore",
             "--infilter=writer8", docx_file,
             "--run-macro", f"macro:///{macro_path}"],
            capture_output=True, text=True, timeout=60
        )
        os.unlink(macro_path)

        if result.returncode != 0:
            print(f"  LibreOffice macro failed (exit {result.returncode}): {result.stderr[:300]}")
            return False
        print("  Page headers added via LibreOffice macro.")
        return True
    except Exception as e:
        print(f"Error adding page headers: {e}")
        return False


def post_process_docx(docx_file: str, fix_flags: dict) -> None:
    """Run all post-processing steps on the DOCX file."""
    add_table_borders_to_docx(docx_file)

    if fix_flags.get("rule4_yellow_bg"):
        add_yellow_bg_to_blockquotes(docx_file)

    if fix_flags.get("rule5_no_separators"):
        remove_paragraph_borders(docx_file)

    if fix_flags.get("rule8_no_empty_pages"):
        remove_empty_pages(docx_file)

    if fix_flags.get("rule9_page_headers"):
        add_page_headers_libreoffice(docx_file)

    if fix_flags.get("rule13_bullet_nonitalic"):
        fix_subchore_heading_style(docx_file)


def main():
    yaml_file   = r'c:\Users\elich\OneDrive\Eddie\Chores\chores_almanac.yaml'
    output_docx = r'c:\Users\elich\OneDrive\Eddie\Chores\chore_almanac.docx'
    output_dir  = r'c:\Users\elich\OneDrive\Eddie\Chores'
    checklist   = r'c:\Users\elich\OneDrive\Eddie\Chores\VALIDATION_CHECKLIST.md'
    report_file = r'c:\Users\elich\OneDrive\Eddie\Chores\inspection_report.txt'
    output_md   = r'c:\Users\elich\OneDrive\Eddie\Chores\chore_almanac.md'
    template    = r'c:\Users\elich\OneDrive\Eddie\Chores\TABLE_TEMPLATE.docx'

    MAX_ATTEMPTS = 3
    fix_flags = dict(DEFAULT_FIX_FLAGS)
    fix_log = []

    print(f'Loading {yaml_file}...')
    data = load_chores(yaml_file)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f'\n=== Attempt {attempt} of {MAX_ATTEMPTS} ===')

        # 1. Generate markdown
        print('Generating almanac markdown...')
        md = generate_markdown(data, year=2026, fix_flags=fix_flags)
        md += generate_purchase_schedule(data)
        md += generate_as_needed(data)

        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(md)

        # 2. Pandoc: markdown → DOCX
        print('Converting to DOCX with pandoc...')
        try:
            pandoc_cmd = ['pandoc', output_md, '-f', 'markdown', '-t', 'docx',
                          '-o', output_docx, '--reference-doc', template, '--standalone']
            subprocess.run(pandoc_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f'Error running pandoc: {e}')
            break
        except FileNotFoundError:
            print('Error: pandoc not found. Install from https://pandoc.org/installing.html')
            break

        if os.path.exists(output_md):
            os.remove(output_md)

        # 3. Post-process DOCX
        post_process_docx(output_docx, fix_flags)

        # 4. Convert to image
        try:
            png_paths = convert_to_image(output_docx, output_dir)
        except Exception as e:
            print(f'Image conversion failed: {e}')
            break

        # 5. Validate image
        print('Validating image against checklist...')
        try:
            results = validate_image(png_paths, checklist)
        except Exception as e:
            print(f'Validation failed: {e}')
            break

        # 6. Write report
        write_report(results, attempt, MAX_ATTEMPTS, fix_log, report_file)

        n_pass = sum(1 for r in results['rules'] if r['status'] == 'PASS')
        n_fail = sum(1 for r in results['rules'] if r['status'] == 'FAIL')
        n_unc  = sum(1 for r in results['rules'] if r['status'] == 'UNCERTAIN')
        print(f'\nResults: {n_pass} PASS, {n_fail} FAIL, {n_unc} UNCERTAIN')

        if all_rules_pass(results):
            print('\nAll rules passed. Document is valid.')
            print(f'Output:  {output_docx}')
            print(f'Preview: {png_paths[0] if png_paths else "none"}')
            return

        if attempt < MAX_ATTEMPTS:
            print(f'\n{n_fail} rule(s) failing. Applying fixes for attempt {attempt + 1}...')
            attempt_fixes(results, fix_flags, fix_log, attempt)
        else:
            escalate_to_user(results, fix_log, report_file)

    print('Done.')


if __name__ == '__main__':
    main()
