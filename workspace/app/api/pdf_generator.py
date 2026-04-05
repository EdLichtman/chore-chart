"""
PDF generation for chore checklists
"""

from datetime import datetime, timedelta
from weasyprint import HTML, CSS
import io
from checklist_service import ChecklistService


class PDFGenerator:
    """Generate PDF checklists from chore data."""

    def __init__(self):
        self.checklist_service = ChecklistService()

    def generate_pdf(self, chores: list) -> bytes:
        """
        Generate a PDF checklist for the current week.

        Args:
            chores: List of chore dictionaries

        Returns:
            PDF file as bytes
        """
        # Get current week start
        week_start = self.checklist_service.get_week_anchor(datetime.now())

        # Generate HTML
        html_content = self._generate_html(chores, week_start)

        # Convert to PDF
        html_doc = HTML(string=html_content, base_url='.')
        pdf_bytes = html_doc.write_pdf()

        return pdf_bytes

    def _generate_html(self, chores: list, week_start: datetime) -> str:
        """Generate HTML content for the checklist."""

        # Group chores
        grouped = self.checklist_service.group_chores_for_checklist(
            chores, week_start
        )

        iso_week = self.checklist_service.get_iso_week(week_start)
        week_display = week_start.strftime('%A, %B %-d, %Y').replace(
            '%-d', str(week_start.day)
        )
        is_odd = iso_week % 2 == 1

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Chore Checklist</title>
            <style>
                {self._get_css()}
            </style>
        </head>
        <body>
            <h1>Chore Checklist</h1>
            <p class="week-header"><strong>Week of: {week_display}</strong> — ISO Week {iso_week} ({'odd' if is_odd else 'even'})</p>

            {self._render_daily_section(grouped['daily'])}
            {self._render_this_week_section(grouped['this_week'])}
            {self._render_weekend_section(grouped['weekend'])}
            {self._render_on_deck_section(grouped['on_deck'])}
            {self._render_inactive_section(grouped['inactive'])}
        </body>
        </html>
        """

        return html

    def _render_daily_section(self, daily_chores: list) -> str:
        """Render the daily chores table."""
        if not daily_chores:
            return ""

        html = "<h2>Daily</h2>"
        html += '<table class="daily-table">'
        html += "<thead><tr><th>Chore</th>"
        for day in ['S', 'M', 'T', 'W', 'T', 'F', 'S']:
            html += f"<th>{day}</th>"
        html += "</tr></thead><tbody>"

        for chore in daily_chores:
            html += f"<tr><td><strong>{chore['name']}</strong></td>"
            for _ in range(7):
                html += '<td class="checkbox-cell">☐</td>'
            html += "</tr>"

        html += "</tbody></table>"
        return html

    def _render_this_week_section(self, this_week_chores: list) -> str:
        """Render the This Week section."""
        if not this_week_chores:
            return ""

        html = "<h2>This Week</h2>"
        html += '<div class="chore-section">'

        for chore in this_week_chores:
            html += '<div class="chore-item">'
            html += f'<input type="checkbox"> <strong>{chore["name"]}</strong>'

            if chore.get('dayConfigurable'):
                html += ' — day: <span class="day-blank">_____</span>'

            if self._is_overdue(chore):
                html += ' <span class="overdue">⚠️ Overdue</span>'

            html += '</div>'

            # Notes
            for note in chore.get('notes', []):
                html += f'<div class="note">{note}</div>'

            # Requirements
            for req in chore.get('requirements', []):
                html += f'<div class="requirement"><input type="checkbox"> {req["name"]}</div>'

        html += "</div>"
        return html

    def _render_weekend_section(self, weekend_chores: list) -> str:
        """Render the Weekend Chores section."""
        if not weekend_chores:
            return ""

        html = "<h2>Weekend Chores</h2>"
        html += '<div class="chore-section">'

        for chore in weekend_chores:
            html += '<div class="chore-item">'
            html += f'<input type="checkbox"> <strong>{chore["name"]}</strong>'

            if chore.get('dayConfigurable'):
                html += ' — day: <span class="day-blank">_____</span>'

            html += '</div>'

            # Notes
            for note in chore.get('notes', []):
                html += f'<div class="note">{note}</div>'

            # Requirements
            for req in chore.get('requirements', []):
                html += f'<div class="requirement"><input type="checkbox"> {req["name"]}</div>'

        html += "</div>"
        return html

    def _render_on_deck_section(self, on_deck_chores: list) -> str:
        """Render the On Deck section."""
        if not on_deck_chores:
            return ""

        html = "<h2 class='page-break-before'>On Deck</h2>"
        html += '<ul class="reference-list">'

        for chore in on_deck_chores:
            due_date = self.checklist_service.get_due_date(chore)
            date_str = due_date.strftime('%B %-d') if due_date else ''
            html += f"<li><strong>{chore['name']}</strong> ({date_str})</li>"

        html += "</ul>"
        return html

    def _render_inactive_section(self, inactive_chores: list) -> str:
        """Render the Inactive section."""
        if not inactive_chores:
            return ""

        html = "<h2>Inactive</h2>"
        html += '<ul class="reference-list">'

        for chore in inactive_chores:
            html += f"<li>{chore['name']}</li>"

        html += "</ul>"
        return html

    def _get_css(self) -> str:
        """Get CSS styles for the PDF."""
        return """
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: Arial, sans-serif;
                color: #333;
                line-height: 1.6;
                max-width: 8.5in;
                margin: 0 auto;
                padding: 0.5in;
            }

            h1 {
                font-size: 1.5em;
                margin-bottom: 0.5em;
                border-bottom: 2px solid #333;
                padding-bottom: 0.25em;
            }

            h2 {
                font-size: 1.1em;
                margin-top: 1.5em;
                margin-bottom: 0.75em;
                border-bottom: 1px solid #ccc;
                padding-bottom: 0.25em;
            }

            .week-header {
                color: #666;
                font-size: 0.9em;
                margin-bottom: 1.5em;
            }

            .daily-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 1.5em;
            }

            .daily-table th,
            .daily-table td {
                border: 1px solid #ccc;
                padding: 0.5em;
                text-align: center;
            }

            .daily-table th {
                background-color: #f0f0f0;
                font-weight: bold;
            }

            .daily-table td:first-child {
                text-align: left;
            }

            .checkbox-cell {
                font-size: 1.2em;
            }

            .chore-section {
                margin-bottom: 1.5em;
            }

            .chore-item {
                margin-bottom: 0.75em;
                display: flex;
                align-items: flex-start;
                gap: 0.5em;
            }

            .chore-item input[type="checkbox"] {
                width: 1.2em;
                height: 1.2em;
                margin-top: 0.1em;
                flex-shrink: 0;
            }

            .day-blank {
                border-bottom: 1px solid #000;
                display: inline-block;
                width: 60px;
                text-align: center;
                margin: 0 4px;
            }

            .overdue {
                color: #d32f2f;
                font-weight: bold;
            }

            .note {
                margin-left: 1.5em;
                color: #666;
                font-size: 0.9em;
                margin-bottom: 0.25em;
            }

            .requirement {
                margin-left: 2em;
                font-size: 0.95em;
                margin-bottom: 0.25em;
            }

            .requirement input[type="checkbox"] {
                width: 1em;
                height: 1em;
                margin-right: 0.3em;
            }

            .reference-list {
                list-style: none;
                margin-left: 0;
                padding-left: 0;
            }

            .reference-list li {
                margin-bottom: 0.4em;
                color: #666;
            }

            .page-break-before {
                page-break-before: always;
            }

            @media print {
                body {
                    padding: 0;
                }
                .chore-section {
                    page-break-inside: avoid;
                }
            }
        """

    def _is_overdue(self, chore: dict) -> bool:
        """Check if a chore is overdue."""
        return self.checklist_service.is_overdue(chore)
