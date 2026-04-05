import { TestBed } from '@angular/core/testing';
import { ChecklistService } from './checklist.service';
import { DateService } from './date.service';
import { Chore, ChoreData } from '../models/chore.model';

// Helper to build a minimal Chore
function makeChore(overrides: Partial<Chore> & { id: string; name: string }): Chore {
  return {
    interval: { n: 1, unit: 'week' },
    dayConfigurable: false,
    weekPin: null,
    dayPin: null,
    notes: [],
    requirements: [],
    annualCadence: [],
    canBeOverdue: false,
    ...overrides,
  };
}

// Helper to build minimal ChoreData
function makeChoreData(categories: Record<string, { label: string; chores: Chore[] }>): ChoreData {
  return {
    gridProperties: {
      print: { columns: 2, rows: 2 },
      web: { columns: 2, rows: 2 },
    },
    daily: [],
    categories,
  };
}

// Fixed "today" used across tests: Wednesday April 8, 2026
const TODAY = new Date(2026, 3, 8); // month is 0-indexed

describe('ChecklistService', () => {
  let service: ChecklistService;
  let dateService: DateService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChecklistService);
    dateService = TestBed.inject(DateService);

    // Pin today to a fixed date for all tests
    jasmine.clock().install();
    jasmine.clock().mockDate(TODAY);
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  // ─────────────────────────────────────────────
  // isPastDue
  // ─────────────────────────────────────────────

  describe('isPastDue', () => {
    it('returns false when canBeOverdue is false', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: false, lastAligned: '2026-01-01', interval: { n: 1, unit: 'month' } });
      expect(service.isPastDue(chore)).toBeFalse();
    });

    it('returns false when lastAligned is missing', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, interval: { n: 1, unit: 'month' } });
      expect(service.isPastDue(chore)).toBeFalse();
    });

    it('returns false when lastAligned is pending', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: 'pending', interval: { n: 1, unit: 'month' } });
      expect(service.isPastDue(chore)).toBeFalse();
    });

    it('returns false when due date is today', () => {
      // lastAligned 30 days ago → due today
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2026-03-09', interval: { n: 1, unit: 'month' } });
      expect(service.isPastDue(chore)).toBeFalse();
    });

    it('returns false when due date is in the future', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2026-03-15', interval: { n: 1, unit: 'month' } });
      expect(service.isPastDue(chore)).toBeFalse();
    });

    it('returns true when due date is in the past — even within grace window', () => {
      // Due April 5 (3 days ago), grace window = 7 days → isOverdue() would return false, isPastDue() returns true
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2026-02-04', interval: { n: 2, unit: 'month' } });
      expect(service.isPastDue(chore)).toBeTrue();
    });

    it('returns true when well outside grace window', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2025-10-01', interval: { n: 6, unit: 'month' } });
      expect(service.isPastDue(chore)).toBeTrue();
    });
  });

  // ─────────────────────────────────────────────
  // isOverdue (grace window respected)
  // ─────────────────────────────────────────────

  describe('isOverdue', () => {
    it('returns false within grace window', () => {
      // Due April 5, 3 days ago — within 7-day grace
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2026-02-04', interval: { n: 2, unit: 'month' } });
      expect(service.isOverdue(chore)).toBeFalse();
    });

    it('returns true outside grace window', () => {
      // Due March 1, 38 days ago — well outside 7-day grace
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2026-02-01', interval: { n: 1, unit: 'month' } });
      expect(service.isOverdue(chore)).toBeTrue();
    });

    it('returns false when canBeOverdue is false', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: false, lastAligned: '2025-01-01', interval: { n: 1, unit: 'month' } });
      expect(service.isOverdue(chore)).toBeFalse();
    });
  });

  // ─────────────────────────────────────────────
  // groupChoresForChecklist — current week
  // ─────────────────────────────────────────────

  describe('groupChoresForChecklist — current week', () => {
    // Current week anchor for Wed April 8 = Sunday April 5
    const weekStart = new Date(2026, 3, 5);

    it('shows chore due this week in its category', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', lastAligned: '2026-03-29', interval: { n: 1, unit: 'week' } });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.categories[0].chores).toContain(chore);
    });

    it('shows overdue canBeOverdue chore in its category', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2025-10-01', interval: { n: 6, unit: 'month' } });
      const data = makeChoreData({ maintenance: { label: 'Maintenance', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.categories[0].chores).toContain(chore);
    });

    it('puts future chore in onDeck', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', lastAligned: '2026-04-05', interval: { n: 2, unit: 'week' } });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.onDeck).toContain(chore);
      expect(result.categories[0].chores).not.toContain(chore);
    });

    it('shows chore with no lastAligned (always show)', () => {
      const chore = makeChore({ id: 'c1', name: 'C1' });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.categories[0].chores).toContain(chore);
    });
  });

  // ─────────────────────────────────────────────
  // groupChoresForChecklist — future week (4-week view)
  // ─────────────────────────────────────────────

  describe('groupChoresForChecklist — future week (week 2)', () => {
    // Week 2 = April 12
    const futureWeekStart = new Date(2026, 3, 12);

    it('shows chore whose due date falls exactly in week 2', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', lastAligned: '2026-04-05', interval: { n: 1, unit: 'week' } });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, futureWeekStart);
      expect(result.categories[0].chores).toContain(chore);
    });

    it('does NOT show a long-interval overdue chore until its next occurrence', () => {
      // lastAligned Oct 1, 6-month interval → next due Sept 26, 2026 — not in week 2
      const chore = makeChore({ id: 'c1', name: 'C1', canBeOverdue: true, lastAligned: '2025-10-01', interval: { n: 6, unit: 'month' } });
      const data = makeChoreData({ maintenance: { label: 'Maintenance', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, futureWeekStart);
      expect(result.categories[0].chores).not.toContain(chore);
      expect(result.onDeck).not.toContain(chore);
    });

    it('shows weekly chore in week 4 by rolling forward the due date', () => {
      // lastAligned April 5 → due April 12 (week 2). Rolling +7 twice → April 26 (week 4).
      const weekStart4 = new Date(2026, 3, 26);
      const chore = makeChore({ id: 'c1', name: 'C1', lastAligned: '2026-04-05', interval: { n: 1, unit: 'week' } });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart4);
      expect(result.categories[0].chores).toContain(chore);
    });

    it('shows chore with no lastAligned in future week too', () => {
      const chore = makeChore({ id: 'c1', name: 'C1' });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, futureWeekStart);
      expect(result.categories[0].chores).toContain(chore);
    });
  });

  // ─────────────────────────────────────────────
  // groupChoresForChecklist — weekPin
  // ─────────────────────────────────────────────

  describe('groupChoresForChecklist — weekPin', () => {
    // ISO week for April 5, 2026: use DateService to check odd/even
    const weekStart = new Date(2026, 3, 5);

    it('shows even-pinned chore when current ISO week is even', () => {
      const isoWeek = dateService.getISOWeek(weekStart);
      const pin = isoWeek % 2 === 0 ? 'even' : 'odd';
      const chore = makeChore({ id: 'c1', name: 'C1', weekPin: pin as 'odd' | 'even', interval: { n: 2, unit: 'week' } });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.categories[0].chores).toContain(chore);
    });

    it('puts wrong-pin chore in onDeck', () => {
      const isoWeek = dateService.getISOWeek(weekStart);
      const wrongPin = isoWeek % 2 === 0 ? 'odd' : 'even';
      const chore = makeChore({ id: 'c1', name: 'C1', weekPin: wrongPin as 'odd' | 'even', interval: { n: 2, unit: 'week' } });
      const data = makeChoreData({ other: { label: 'Other', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.onDeck).toContain(chore);
      expect(result.categories[0].chores).not.toContain(chore);
    });
  });

  // ─────────────────────────────────────────────
  // groupChoresForChecklist — all categories always present
  // ─────────────────────────────────────────────

  describe('groupChoresForChecklist — category always present', () => {
    const weekStart = new Date(2026, 3, 5);

    it('includes empty categories in the result', () => {
      const chore = makeChore({ id: 'c1', name: 'C1', lastAligned: '2026-04-05', interval: { n: 4, unit: 'week' } });
      const data = makeChoreData({ maintenance: { label: 'Maintenance', chores: [chore] } });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.categories.length).toBe(1);
      expect(result.categories[0].chores.length).toBe(0);
    });
  });

  // ─────────────────────────────────────────────
  // gridProperties column calculation
  // ─────────────────────────────────────────────

  describe('gridProperties column hints', () => {
    it('uses gridProperties.web.columns=2 → col-md-6', () => {
      // This is tested via ChecklistComponent.categoryColClass — service just returns categories
      // Verify 4 categories are returned so component can compute grid
      const weekStart = new Date(2026, 3, 5);
      const data = makeChoreData({
        upstairs:    { label: 'Upstairs',    chores: [] },
        downstairs:  { label: 'Downstairs',  chores: [] },
        other:       { label: 'Other',       chores: [] },
        maintenance: { label: 'Maintenance', chores: [] },
      });
      const result = service.groupChoresForChecklist(data, weekStart);
      expect(result.categories.length).toBe(4);
    });
  });
});
