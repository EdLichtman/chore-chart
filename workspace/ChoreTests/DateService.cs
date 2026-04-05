namespace ChoreTests;

public class DateService
{
    /// <summary>
    /// Calculate the Sunday (week anchor) for a given date.
    /// Uses Wed/Thu boundary: Sun-Wed is current week, Thu-Sat is next week.
    /// </summary>
    public DateTime GetWeekAnchor(DateTime? date = null)
    {
        var d = (date ?? DateTime.Now).Date;
        var dayOfWeek = (int)d.DayOfWeek;

        // If it's Sun-Wed (0-3), anchor to this Sunday
        // If it's Thu-Sat (4-6), anchor to next Sunday
        int daysToSubtract;
        if (dayOfWeek >= 0 && dayOfWeek <= 3)
        {
            daysToSubtract = dayOfWeek;
        }
        else
        {
            daysToSubtract = dayOfWeek - 7;
        }

        return d.AddDays(-daysToSubtract);
    }

    /// <summary>
    /// Get ISO week number (1-52).
    /// </summary>
    public int GetISOWeek(DateTime? date = null)
    {
        var d = (date ?? DateTime.Now).Date;
        d = d.AddDays(4 - (int)(d.DayOfWeek == 0 ? 7 : d.DayOfWeek));
        var yearStart = new DateTime(d.Year, 1, 1);
        return (int)Math.Ceiling((double)(d - yearStart).Days / 7 + 1);
    }

    /// <summary>
    /// Add days to a date.
    /// </summary>
    public DateTime AddDays(DateTime date, int days)
    {
        return date.AddDays(days);
    }

    /// <summary>
    /// Calculate the next due date for a chore based on lastAligned and interval.
    /// </summary>
    public DateTime? GetNextDueDate(string? lastAligned, Interval interval)
    {
        if (string.IsNullOrEmpty(lastAligned) || lastAligned == "pending")
        {
            return null;
        }

        if (!DateTime.TryParse(lastAligned, out var lastAlignedDate))
        {
            return null;
        }

        lastAlignedDate = lastAlignedDate.Date;

        int daysToAdd = interval.Unit switch
        {
            "day" => interval.N,
            "week" => interval.N * 7,
            "month" => interval.N * 30,
            "year" => interval.N * 365,
            _ => 0
        };

        return lastAlignedDate.AddDays(daysToAdd);
    }

    /// <summary>
    /// Format a date as YYYY-MM-DD.
    /// </summary>
    public string FormatDate(DateTime date)
    {
        return date.ToString("yyyy-MM-dd");
    }

    /// <summary>
    /// Check if a date is within the given week (Sunday to Saturday).
    /// </summary>
    public bool IsInWeek(DateTime date, DateTime weekStart)
    {
        var weekEnd = weekStart.AddDays(6);
        date = date.Date;
        weekStart = weekStart.Date;
        weekEnd = weekEnd.Date;

        return date >= weekStart && date <= weekEnd;
    }

    /// <summary>
    /// Check if today is before the week start.
    /// </summary>
    public bool IsTodayBeforeWeek(DateTime weekStart)
    {
        var today = DateTime.Now.Date;
        var ws = weekStart.Date;
        return today < ws;
    }
}
