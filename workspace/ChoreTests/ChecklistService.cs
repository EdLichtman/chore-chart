namespace ChoreTests;

public class ChecklistService
{
    private readonly DateService _dateService;

    public ChecklistService(DateService dateService)
    {
        _dateService = dateService;
    }

    /// <summary>
    /// Determine the effective interval for a chore at a given date,
    /// accounting for annual cadence overrides.
    /// </summary>
    public Interval? GetEffectiveInterval(Chore chore, DateTime date)
    {
        if (IsInactiveOnDate(chore, date))
        {
            return null;
        }

        // Find the latest cadence entry that applies
        Interval? effectiveInterval = chore.Interval;
        DateTime? latestStart = null;

        foreach (var entry in chore.AnnualCadence)
        {
            var entryDate = ParseMMDD(entry.StartDate, date.Year);

            // If entry is in the past or today, it applies
            if (entryDate <= date)
            {
                if (latestStart == null || entryDate > latestStart)
                {
                    latestStart = entryDate;
                    if (entry.Interval != null)
                    {
                        effectiveInterval = entry.Interval;
                    }
                }
            }
        }

        return effectiveInterval;
    }

    /// <summary>
    /// Check if a chore is inactive on a given date.
    /// </summary>
    public bool IsInactiveOnDate(Chore chore, DateTime date)
    {
        foreach (var entry in chore.AnnualCadence)
        {
            if (entry.IsInactive)
            {
                var startDate = ParseMMDD(entry.StartDate, date.Year);
                var nextEntry = GetNextCadenceEntry(chore, entry);

                DateTime? endDate = null;
                if (nextEntry != null)
                {
                    endDate = ParseMMDD(nextEntry.StartDate, date.Year);
                }

                // Check if date is within inactive range
                if (date >= startDate && (endDate == null || date < endDate))
                {
                    return true;
                }
            }
        }
        return false;
    }

    /// <summary>
    /// Get the next cadence entry after the given one.
    /// </summary>
    private CadenceEntry? GetNextCadenceEntry(Chore chore, CadenceEntry current)
    {
        var idx = chore.AnnualCadence.IndexOf(current);
        if (idx >= 0 && idx < chore.AnnualCadence.Count - 1)
        {
            return chore.AnnualCadence[idx + 1];
        }
        return null;
    }

    /// <summary>
    /// Check if a date falls on a weekend (Saturday or Sunday).
    /// </summary>
    private bool IsWeekendDay(DateTime date)
    {
        return date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday;
    }

    /// <summary>
    /// Group chores by section for the weekly checklist.
    /// </summary>
    public ChecklistData GroupChoresForChecklist(List<Chore> chores, DateTime weekStart)
    {
        var daily = new List<Chore>();
        var thisWeek = new List<Chore>();
        var weekend = new List<Chore>();
        var onDeck = new List<Chore>();
        var inactive = new List<Chore>();

        foreach (var chore in chores)
        {
            // Check if inactive
            if (IsInactiveOnDate(chore, weekStart))
            {
                inactive.Add(chore);
                continue;
            }

            // Daily chores
            if (chore.Interval.IsDaily)
            {
                daily.Add(chore);
                continue;
            }

            // Check weekPin (for bi-weekly chores)
            if (chore.Interval.IsBiWeekly && chore.WeekPin != null)
            {
                var currentWeek = _dateService.GetISOWeek(weekStart);
                var isOdd = currentWeek % 2 == 1;

                if (chore.WeekPin == "odd" && !isOdd)
                {
                    onDeck.Add(chore);
                    continue;
                }
                if (chore.WeekPin == "even" && isOdd)
                {
                    onDeck.Add(chore);
                    continue;
                }
            }

            // Determine due date
            var dueDate = _dateService.GetNextDueDate(chore.LastAligned, chore.Interval);

            if (dueDate == null)
            {
                // Pending chores without due date go to thisWeek
                if (chore.LastAligned == "pending")
                {
                    thisWeek.Add(chore);
                }
                continue;
            }

            // Check which section
            var weekEnd = weekStart.AddDays(6);

            if (_dateService.IsInWeek(dueDate.Value, weekStart))
            {
                // Place in weekend or thisWeek based on actual due date
                if (IsWeekendDay(dueDate.Value))
                {
                    weekend.Add(chore);
                }
                else
                {
                    thisWeek.Add(chore);
                }
            }
            else if (dueDate > weekEnd && dueDate <= _dateService.AddDays(weekEnd, 14))
            {
                onDeck.Add(chore);
            }
            else
            {
                onDeck.Add(chore);
            }
        }

        return new ChecklistData(daily, thisWeek, weekend, onDeck, inactive);
    }

    /// <summary>
    /// Parse a MM-DD string to a DateTime (with given year).
    /// </summary>
    private DateTime ParseMMDD(string mmdd, int year)
    {
        var parts = mmdd.Split('-');
        var month = int.Parse(parts[0]);
        var day = int.Parse(parts[1]);
        return new DateTime(year, month, day);
    }
}
