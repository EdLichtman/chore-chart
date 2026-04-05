namespace ChoreTests;

public record Interval(int N, string Unit)
{
    public bool IsDaily => Unit == "day" && N == 1;
    public bool IsBiWeekly => Unit == "week" && N == 2;
}

public record Requirement(string Id, string Name, Interval Interval, string? LastAligned);

public record CadenceEntry(string StartDate, Interval? Interval = null, string? Status = null)
{
    public bool IsInactive => Status == "inactive";
}

public record Chore(
    string Id,
    string Name,
    Interval Interval,
    bool Weekend,
    bool DayConfigurable,
    string? WeekPin,
    int? DayPin,
    string? LastAligned,
    List<string> Notes,
    List<string> SynchronizedWith,
    List<Requirement> Requirements,
    List<CadenceEntry> AnnualCadence
);

public record ChecklistData(
    List<Chore> Daily,
    List<Chore> ThisWeek,
    List<Chore> Weekend,
    List<Chore> OnDeck,
    List<Chore> Inactive
);
