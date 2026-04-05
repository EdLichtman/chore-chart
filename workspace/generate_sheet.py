#!/usr/bin/env python3
"""Generate HTML checklist from chores.json"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

def get_week_anchor(date: datetime) -> datetime:
    """Calculate Sunday of the week containing the given date."""
    days_since_sunday = date.weekday() + 1  # Monday=0, Sunday=6 -> Sunday=0
    if days_since_sunday == 7:
        days_since_sunday = 0
    return date - timedelta(days=days_since_sunday)

def get_iso_week(date: datetime) -> int:
    """Get ISO week number (1-52)."""
    return date.isocalendar()[1]

def is_chore_due_this_week(chore: dict, week_start: datetime) -> bool:
    """Check if a chore is due this week."""
    if chore["lastAligned"] == "pending":
        return True

    last_aligned = datetime.fromisoformat(chore["lastAligned"])
    interval_days = 0

    n = chore["interval"]["n"]
    unit = chore["interval"]["unit"]

    if unit == "day":
        return chore["interval"]["n"] == 1  # Daily chores always show
    elif unit == "week":
        interval_days = n * 7
    elif unit == "month":
        # Rough estimate: 30 days per month
        interval_days = n * 30
    else:  # year
        interval_days = n * 365

    due_date = last_aligned + timedelta(days=interval_days)
    week_end = week_start + timedelta(days=6)

    # Check bi-weekly week pin
    if unit == "week" and n == 2 and chore.get("weekPin"):
        current_iso = get_iso_week(week_start)
        week_pin = chore["weekPin"]
        is_odd = current_iso % 2 == 1
        if week_pin == "odd" and not is_odd:
            return False
        if week_pin == "even" and is_odd:
            return False

    return week_start <= due_date <= week_end

def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&#39;"))

def generate_checklist_html(date: Optional[datetime] = None) -> str:
    """Generate HTML checklist from chores.json."""

    if date is None:
        date = datetime.now()

    script_dir = Path(__file__).parent
    chores_file = script_dir / "chores.json"

    with open(chores_file, "r") as f:
        data = json.load(f)

    chores = data["chores"]
    week_start = get_week_anchor(date)
    iso_week = get_iso_week(week_start)
    week_start_str = week_start.strftime("%A, %B %-d, %Y").replace("%-d", str(week_start.day))

    # Separate chores by type
    daily_chores = [c for c in chores if c["interval"]["unit"] == "day"]
    this_week_chores = [c for c in chores if not c["weekend"] and is_chore_due_this_week(c, week_start)]
    weekend_chores = [c for c in chores if c["weekend"] and is_chore_due_this_week(c, week_start)]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chore Checklist</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f9f9f9;
            color: #333;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        h2 {{
            background: #e8e8e8;
            padding: 10px;
            margin-top: 20px;
            border-left: 4px solid #333;
        }}
        .container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }}
        .section {{
            background: white;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .section h3 {{
            margin-top: 0;
            color: #555;
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
        }}
        ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        li {{
            margin: 8px 0;
            line-height: 1.6;
        }}
        input[type="checkbox"] {{
            margin-right: 8px;
            cursor: pointer;
        }}
        .sub-task {{
            margin-left: 20px;
            color: #666;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border: 1px solid #ddd;
            margin: 10px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
        }}
        th {{
            background: #f0f0f0;
            font-weight: bold;
        }}
        .overdue {{
            color: #d32f2f;
            font-weight: bold;
        }}
        .on-deck, .inactive {{
            color: #666;
        }}
        .day-fill {{
            display: inline-block;
            border-bottom: 1px solid #333;
            width: 60px;
            text-align: center;
        }}
        @media (max-width: 900px) {{
            .container {{
                grid-template-columns: 1fr;
            }}
        }}
        @media print {{
            body {{ background: white; }}
            .section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <h1>Chore Checklist</h1>
    <p style="text-align: center; font-size: 16px;"><strong>Week of: {week_start_str}</strong> — ISO Week {iso_week} ({'odd' if iso_week % 2 == 1 else 'even'})</p>
"""

    # Daily chores table
    if daily_chores:
        html += """
    <h2>Daily</h2>
    <table>
        <tr>
            <th>Chore</th>
            <th>S</th>
            <th>M</th>
            <th>T</th>
            <th>W</th>
            <th>T</th>
            <th>F</th>
            <th>S</th>
        </tr>
"""
        for chore in daily_chores:
            html += f"""        <tr>
            <td style="text-align: left;">{escape_html(chore['name'])}</td>
            <td><input type="checkbox"></td>
            <td><input type="checkbox"></td>
            <td><input type="checkbox"></td>
            <td><input type="checkbox"></td>
            <td><input type="checkbox"></td>
            <td><input type="checkbox"></td>
            <td><input type="checkbox"></td>
        </tr>
"""
        html += "    </table>\n"

    # This Week & Weekend Chores
    if this_week_chores or weekend_chores:
        html += """
    <h2>This Week & Weekend Chores</h2>
    <div class="container">
"""

        # This Week section
        html += """        <div class="section">
            <h3>This Week</h3>
            <ul>
"""
        for chore in this_week_chores:
            day_str = ""
            if chore["dayConfigurable"]:
                day_str = ' — day: <span class="day-fill"></span>'

            html += f"""                <li><input type="checkbox"> {escape_html(chore['name'])}{day_str}</li>
"""

            # Add notes
            for note in chore.get("notes", []):
                html += f"""                    <ul class="sub-task"><li>{escape_html(note)}</li></ul>
"""

            # Add requirements
            for req in chore.get("requirements", []):
                html += f"""                    <ul class="sub-task"><li><input type="checkbox"> {escape_html(req['name'])}</li></ul>
"""

        html += """            </ul>
        </div>

        <div class="section">
            <h3>Weekend Chores</h3>
            <ul>
"""

        for chore in weekend_chores:
            html += f"""                <li><input type="checkbox"> {escape_html(chore['name'])}</li>
"""

            # Add notes
            for note in chore.get("notes", []):
                html += f"""                    <ul class="sub-task"><li>{escape_html(note)}</li></ul>
"""

            # Add requirements
            for req in chore.get("requirements", []):
                html += f"""                    <ul class="sub-task"><li><input type="checkbox"> {escape_html(req['name'])}</li></ul>
"""

        html += """            </ul>
        </div>
    </div>
"""

    # On Deck (next 1-2 weeks)
    html += """
    <h2>On Deck</h2>
    <ul class="on-deck">
        <li>Mop First Floor (April 12)</li>
        <li>Vacuum Downstairs (April 12)</li>
        <li>Clean Little Trashes Around House (April 15)</li>
    </ul>

    <h2>Inactive</h2>
    <ul class="inactive">
        <li>Mow (resumes May 1)</li>
    </ul>

</body>
</html>
"""

    return html

if __name__ == "__main__":
    html = generate_checklist_html()
    output_file = Path(__file__).parent / "checklist.html"
    with open(output_file, "w") as f:
        f.write(html)
    print(f"Generated {output_file}")
