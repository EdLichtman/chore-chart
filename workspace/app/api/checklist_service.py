"""
Checklist service for Python backend
Handles date calculations, chore grouping, and interval logic
"""

from datetime import datetime, timedelta


class ChecklistService:
    """Service for checklist logic and calculations."""

    def get_week_anchor(self, date: datetime = None) -> datetime:
        """
        Get the Sunday (week start) for a given date.
        Uses Wed/Thu boundary: Sun-Wed is current week, Thu-Sat is next week.
        """
        if date is None:
            date = datetime.now()

        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_of_week = date.weekday()  # Monday=0, Sunday=6

        # Convert to Sunday=0, Monday=1, ..., Saturday=6
        dow = (day_of_week + 1) % 7

        # If Sun-Wed (0-3), anchor to this Sunday
        # If Thu-Sat (4-6), anchor to next Sunday
        if dow <= 3:
            days_back = dow
        else:
            days_back = dow - 7

        return date - timedelta(days=days_back)

    def get_iso_week(self, date: datetime = None) -> int:
        """Get ISO week number (1-52)."""
        if date is None:
            date = datetime.now()

        d = date.replace(hour=0, minute=0, second=0, microsecond=0)
        d = d + timedelta(days=4 - (d.weekday() or 7))
        year_start = datetime(d.year, 1, 1)
        return ((d - year_start).days + 1) // 7 + 1

    def add_days(self, date: datetime, days: int) -> datetime:
        """Add days to a date."""
        return date + timedelta(days=days)

    def get_next_due_date(
        self, last_aligned: str = None, interval: dict = None
    ) -> datetime:
        """
        Calculate next due date based on lastAligned and interval.
        """
        if not last_aligned or last_aligned == 'pending':
            return None

        try:
            last_aligned_date = datetime.fromisoformat(last_aligned).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        except (ValueError, TypeError):
            return None

        if not interval:
            return None

        n = interval.get('n', 1)
        unit = interval.get('unit', 'week')

        if unit == 'day':
            days_to_add = n
        elif unit == 'week':
            days_to_add = n * 7
        elif unit == 'month':
            days_to_add = n * 30  # Rough estimate
        elif unit == 'year':
            days_to_add = n * 365
        else:
            return None

        return last_aligned_date + timedelta(days=days_to_add)

    def format_date(self, date: datetime) -> str:
        """Format date as YYYY-MM-DD."""
        return date.strftime('%Y-%m-%d')

    def is_in_week(self, date: datetime, week_start: datetime) -> bool:
        """Check if a date is within the given week (Sunday to Saturday)."""
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6)

        return week_start <= date <= week_end

    def is_inactive_on_date(self, chore: dict, date: datetime) -> bool:
        """Check if a chore is inactive on a given date."""
        for entry in chore.get('annualCadence', []):
            if entry.get('status') == 'inactive':
                start_date = self._parse_mmdd(
                    entry.get('startDate', '01-01'), date.year
                )
                next_entry = self._get_next_cadence_entry(chore, entry)
                end_date = None
                if next_entry:
                    end_date = self._parse_mmdd(
                        next_entry.get('startDate', '01-01'), date.year
                    )

                if date >= start_date and (not end_date or date < end_date):
                    return True

        return False

    def is_overdue(self, chore: dict) -> bool:
        """Check if a chore is overdue as of today."""
        last_aligned = chore.get('lastAligned')
        if not last_aligned or last_aligned == 'pending':
            return last_aligned == 'pending'

        due_date = self.get_next_due_date(last_aligned, chore.get('interval'))
        if not due_date:
            return False

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return due_date < today

    def get_due_date(self, chore: dict) -> datetime:
        """Get the due date for a chore."""
        return self.get_next_due_date(
            chore.get('lastAligned'), chore.get('interval')
        )

    def is_due_this_week(self, chore: dict, week_start: datetime) -> bool:
        """Determine if a chore is due within the given week."""
        interval = chore.get('interval', {})

        # Daily chores always appear
        if interval.get('unit') == 'day' and interval.get('n') == 1:
            return not self.is_inactive_on_date(chore, week_start)

        # Check if inactive
        if self.is_inactive_on_date(chore, week_start):
            return False

        # Check weekPin (for bi-weekly chores)
        if (
            interval.get('unit') == 'week'
            and interval.get('n') == 2
            and chore.get('weekPin')
        ):
            current_week = self.get_iso_week(week_start)
            is_odd = current_week % 2 == 1

            if chore.get('weekPin') == 'odd' and not is_odd:
                return False
            if chore.get('weekPin') == 'even' and is_odd:
                return False

        # If lastAligned is pending, only daily chores are due
        last_aligned = chore.get('lastAligned')
        if last_aligned == 'pending' or last_aligned is None:
            return interval.get('unit') == 'day'

        # Calculate next due date
        due_date = self.get_next_due_date(last_aligned, interval)
        if not due_date:
            return False

        return self.is_in_week(due_date, week_start)

    def group_chores_for_checklist(self, chores: list, week_start: datetime):
        """
        Group chores by section for the weekly checklist.
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        daily = []
        this_week = []
        weekend = []
        on_deck = []
        inactive = []

        for chore in chores:
            # Check if inactive
            if self.is_inactive_on_date(chore, week_start):
                inactive.append(chore)
                continue

            # Daily chores
            interval = chore.get('interval', {})
            if interval.get('unit') == 'day' and interval.get('n') == 1:
                daily.append(chore)
                continue

            # Check weekPin
            if (
                interval.get('unit') == 'week'
                and interval.get('n') == 2
                and chore.get('weekPin')
            ):
                current_week = self.get_iso_week(week_start)
                is_odd = current_week % 2 == 1

                if chore.get('weekPin') == 'odd' and not is_odd:
                    on_deck.append(chore)
                    continue
                if chore.get('weekPin') == 'even' and is_odd:
                    on_deck.append(chore)
                    continue

            # Determine due date
            due_date = self.get_next_due_date(
                chore.get('lastAligned'), interval
            )

            if not due_date:
                # Pending chores go to appropriate section
                if chore.get('lastAligned') == 'pending':
                    if chore.get('weekend'):
                        weekend.append(chore)
                    else:
                        this_week.append(chore)
                continue

            # Check which section
            week_end = week_start + timedelta(days=6)

            if self.is_in_week(due_date, week_start):
                if chore.get('weekend'):
                    weekend.append(chore)
                else:
                    this_week.append(chore)
            elif due_date > week_end and due_date <= week_end + timedelta(days=14):
                on_deck.append(chore)
            else:
                on_deck.append(chore)

        return {
            'daily': daily,
            'this_week': this_week,
            'weekend': weekend,
            'on_deck': on_deck,
            'inactive': inactive,
        }

    def _parse_mmdd(self, mmdd: str, year: int) -> datetime:
        """Parse MM-DD string to datetime with given year."""
        parts = mmdd.split('-')
        month, day = int(parts[0]), int(parts[1])
        return datetime(year, month, day)

    def _get_next_cadence_entry(self, chore: dict, current: dict):
        """Get the next cadence entry after the given one."""
        entries = chore.get('annualCadence', [])
        try:
            idx = entries.index(current)
            if idx >= 0 and idx < len(entries) - 1:
                return entries[idx + 1]
        except ValueError:
            pass
        return None
