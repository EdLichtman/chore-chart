namespace ChoreTests;

using Xunit;

public class ChecklistServiceTests
{
    private readonly ChecklistService _service;
    private readonly DateService _dateService;

    public ChecklistServiceTests()
    {
        _dateService = new DateService();
        _service = new ChecklistService(_dateService);
    }

    private Chore CreateChore(
        string id = "test",
        string name = "Test Chore",
        int intervalN = 1,
        string intervalUnit = "day",
        bool weekend = false,
        string? weekPin = null,
        string? lastAligned = null)
    {
        return new Chore(
            Id: id,
            Name: name,
            Interval: new Interval(intervalN, intervalUnit),
            Weekend: weekend,
            DayConfigurable: false,
            WeekPin: weekPin,
            DayPin: null,
            LastAligned: lastAligned,
            Notes: new(),
            SynchronizedWith: new(),
            Requirements: new(),
            AnnualCadence: new()
        );
    }

    #region Daily Chores

    [Fact]
    public void DailyChores_AlwaysPlacedInDailySection()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var chores = new List<Chore>
        {
            CreateChore(id: "daily1", name: "Daily Task 1"),
            CreateChore(id: "daily2", name: "Daily Task 2"),
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Equal(2, result.Daily.Count);
        Assert.Empty(result.ThisWeek);
        Assert.Empty(result.Weekend);
        Assert.Empty(result.OnDeck);
    }

    #endregion

    #region Weekly Chores

    [Fact]
    public void WeeklyChore_DueThisWeek_PlacedInThisWeekSection()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var dueDate = new DateTime(2026, 4, 7); // Tuesday
        var lastAligned = dueDate.AddDays(-7).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "weekly1",
                name: "Weekly Task",
                intervalN: 1,
                intervalUnit: "week",
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.ThisWeek);
        Assert.Equal("weekly1", result.ThisWeek[0].Id);
    }

    [Fact]
    public void WeeklyChore_DueNextWeek_PlacedInOnDeckSection()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var dueDate = new DateTime(2026, 4, 15); // Following Wednesday
        var lastAligned = dueDate.AddDays(-7).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "weekly1",
                name: "Weekly Task",
                intervalN: 1,
                intervalUnit: "week",
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.OnDeck);
    }

    #endregion

    #region Weekend vs Weekday Classification

    [Fact]
    public void Chore_DueOnSaturday_PlacedInWeekendSection()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var saturday = new DateTime(2026, 4, 11); // Saturday (same week)
        var lastAligned = saturday.AddDays(-7).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "mowing",
                name: "Mow Lawn",
                intervalN: 1,
                intervalUnit: "week",
                weekend: true,
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.Weekend);
        Assert.Equal("mowing", result.Weekend[0].Id);
        Assert.Empty(result.ThisWeek);
    }

    [Fact]
    public void Chore_DueOnSunday_PlacedInWeekendSection()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var nextSunday = new DateTime(2026, 4, 12); // Sunday (next week)
        var lastAligned = nextSunday.AddDays(-7).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "chore1",
                name: "Sunday Chore",
                intervalN: 1,
                intervalUnit: "week",
                weekend: true,
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, nextSunday);

        // Assert
        Assert.Single(result.Weekend);
    }

    [Fact]
    public void Chore_DueOnMonday_PlacedInThisWeekNotWeekend()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var monday = new DateTime(2026, 4, 6); // Monday
        var lastAligned = monday.AddDays(-7).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "chore1",
                name: "Monday Chore",
                intervalN: 1,
                intervalUnit: "week",
                weekend: true, // Has weekend flag but due on weekday
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.ThisWeek);
        Assert.Empty(result.Weekend);
    }

    [Fact]
    public void Chore_WithWeekendFlag_ButDueWeekday_IgnoresWeekendFlag()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var tuesday = new DateTime(2026, 4, 7); // Tuesday
        var lastAligned = tuesday.AddDays(-7).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "lawn_care",
                name: "Lawn Care",
                intervalN: 2,
                intervalUnit: "week",
                weekend: true, // Should use actual due date
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.ThisWeek);
        Assert.Empty(result.Weekend);
    }

    #endregion

    #region Bi-Weekly with WeekPin

    [Fact]
    public void BiWeeklyChore_OddWeekPin_ShowsOnOddWeeks()
    {
        // Arrange
        var oddWeekStart = new DateTime(2026, 4, 5); // Week 15 (odd)
        var lastAligned = oddWeekStart.AddDays(-14).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "biweekly1",
                name: "Bi-Weekly Task",
                intervalN: 2,
                intervalUnit: "week",
                weekPin: "odd",
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, oddWeekStart);

        // Assert
        Assert.Single(result.ThisWeek);
    }

    [Fact]
    public void BiWeeklyChore_OddWeekPin_HiddenOnEvenWeeks()
    {
        // Arrange
        var evenWeekStart = new DateTime(2026, 4, 12); // Week 16 (even)
        var lastAligned = evenWeekStart.AddDays(-14).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "biweekly1",
                name: "Bi-Weekly Task",
                intervalN: 2,
                intervalUnit: "week",
                weekPin: "odd",
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, evenWeekStart);

        // Assert
        Assert.Single(result.OnDeck);
        Assert.Empty(result.ThisWeek);
    }

    [Fact]
    public void BiWeeklyChore_EvenWeekPin_ShowsOnEvenWeeks()
    {
        // Arrange
        var evenWeekStart = new DateTime(2026, 4, 12); // Week 16 (even)
        var lastAligned = evenWeekStart.AddDays(-14).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "biweekly1",
                name: "Bi-Weekly Task",
                intervalN: 2,
                intervalUnit: "week",
                weekPin: "even",
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, evenWeekStart);

        // Assert
        Assert.Single(result.ThisWeek);
    }

    [Fact]
    public void BiWeeklyChore_EvenWeekPin_HiddenOnOddWeeks()
    {
        // Arrange
        var oddWeekStart = new DateTime(2026, 4, 5); // Week 15 (odd)
        var lastAligned = oddWeekStart.AddDays(-14).ToString("yyyy-MM-dd");

        var chores = new List<Chore>
        {
            CreateChore(
                id: "biweekly1",
                name: "Bi-Weekly Task",
                intervalN: 2,
                intervalUnit: "week",
                weekPin: "even",
                lastAligned: lastAligned
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, oddWeekStart);

        // Assert
        Assert.Single(result.OnDeck);
        Assert.Empty(result.ThisWeek);
    }

    #endregion

    #region Pending Chores

    [Fact]
    public void PendingChore_NoLastAligned_PlacedInThisWeek()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5);
        var chores = new List<Chore>
        {
            CreateChore(
                id: "pending1",
                name: "Pending Chore",
                intervalN: 1,
                intervalUnit: "week",
                lastAligned: "pending"
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.ThisWeek);
        Assert.Empty(result.Weekend);
    }

    #endregion

    #region Inactive Chores

    [Fact]
    public void InactiveChore_PlacedInInactiveSection()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5);
        var chores = new List<Chore>
        {
            new Chore(
                Id: "inactive1",
                Name: "Inactive Chore",
                Interval: new Interval(1, "week"),
                Weekend: false,
                DayConfigurable: false,
                WeekPin: null,
                DayPin: null,
                LastAligned: "2026-03-01",
                Notes: new(),
                SynchronizedWith: new(),
                Requirements: new(),
                AnnualCadence: new List<CadenceEntry>
                {
                    new CadenceEntry("04-01", Status: "inactive")
                }
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.Inactive);
    }

    #endregion

    #region Edge Cases

    [Fact]
    public void MultipleChores_CorrectlyCategorized()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5); // Sunday
        var chores = new List<Chore>
        {
            // Daily
            CreateChore(id: "daily1", name: "Daily Task"),

            // This week - due Tuesday
            CreateChore(
                id: "week1",
                name: "Week Task",
                intervalN: 1,
                intervalUnit: "week",
                lastAligned: "2026-03-31"
            ),

            // Weekend - due Saturday
            CreateChore(
                id: "weekend1",
                name: "Saturday Task",
                intervalN: 1,
                intervalUnit: "week",
                weekend: true,
                lastAligned: "2026-04-04"
            ),

            // Bi-weekly (odd week)
            CreateChore(
                id: "biweekly1",
                name: "Bi-Weekly",
                intervalN: 2,
                intervalUnit: "week",
                weekPin: "odd",
                lastAligned: "2026-03-22"
            ),

            // Pending
            CreateChore(
                id: "pending1",
                name: "Pending",
                intervalN: 1,
                intervalUnit: "week",
                lastAligned: "pending"
            )
        };

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Single(result.Daily);
        Assert.Equal(2, result.ThisWeek.Count); // Week task + pending
        Assert.Single(result.Weekend);
        Assert.Empty(result.OnDeck);
        Assert.Empty(result.Inactive);
    }

    [Fact]
    public void NoChores_ReturnsEmptyLists()
    {
        // Arrange
        var weekStart = new DateTime(2026, 4, 5);
        var chores = new List<Chore>();

        // Act
        var result = _service.GroupChoresForChecklist(chores, weekStart);

        // Assert
        Assert.Empty(result.Daily);
        Assert.Empty(result.ThisWeek);
        Assert.Empty(result.Weekend);
        Assert.Empty(result.OnDeck);
        Assert.Empty(result.Inactive);
    }

    #endregion
}
