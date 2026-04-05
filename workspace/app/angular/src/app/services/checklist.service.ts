import { Injectable } from '@angular/core';
import { Chore, ChecklistChore, CadenceEntry, Interval } from '../models/chore.model';
import { DateService } from './date.service';

@Injectable({
  providedIn: 'root',
})
export class ChecklistService {
  constructor(private dateService: DateService) {}

  /**
   * Determine the effective interval for a chore at a given date,
   * accounting for annual cadence overrides.
   */
  getEffectiveInterval(chore: Chore, date: Date): Interval | null {
    const mmdd = this.formatMMDD(date);
    const isInactive = this.isInactiveOnDate(chore, date);

    if (isInactive) {
      return null;
    }

    // Find the latest cadence entry that applies
    let effectiveInterval = chore.interval;
    let latestStart: Date | null = null;

    for (const entry of chore.annualCadence) {
      const entryDate = this.parseMMDD(entry.startDate, date.getFullYear());

      // If entry is in the past or today, it applies
      if (entryDate <= date) {
        if (!latestStart || entryDate > latestStart) {
          latestStart = entryDate;
          if (entry.interval) {
            effectiveInterval = entry.interval;
          }
        }
      }
    }

    return effectiveInterval;
  }

  /**
   * Check if a chore is inactive on a given date.
   */
  isInactiveOnDate(chore: Chore, date: Date): boolean {
    // If there's annual cadence, check if the date is before the first active entry
    if (chore.annualCadence.length > 0) {
      const firstEntry = chore.annualCadence[0];
      const firstStartDate = this.parseMMDD(firstEntry.startDate, date.getFullYear());

      // If the date is before the first cadence entry, it's inactive
      if (date < firstStartDate) {
        return true;
      }
    }

    // Check for explicit inactive periods
    for (const entry of chore.annualCadence) {
      if (entry.status === 'inactive') {
        const startDate = this.parseMMDD(entry.startDate, date.getFullYear());
        const nextEntry = this.getNextCadenceEntry(chore, entry);

        let endDate: Date | null = null;
        if (nextEntry) {
          endDate = this.parseMMDD(nextEntry.startDate, date.getFullYear());
        }

        // Check if date is within inactive range
        if (date >= startDate && (!endDate || date < endDate)) {
          return true;
        }
      }
    }
    return false;
  }

  /**
   * Get the next cadence entry after the given one.
   */
  private getNextCadenceEntry(
    chore: Chore,
    current: CadenceEntry
  ): CadenceEntry | null {
    const idx = chore.annualCadence.indexOf(current);
    if (idx >= 0 && idx < chore.annualCadence.length - 1) {
      return chore.annualCadence[idx + 1];
    }
    return null;
  }

  /**
   * Determine if a chore is due within the given week.
   */
  isDueThisWeek(chore: Chore, weekStart: Date): boolean {
    // Daily chores always appear
    if (chore.interval.unit === 'day' && chore.interval.n === 1) {
      return !this.isInactiveOnDate(chore, weekStart);
    }

    // Check if inactive
    if (this.isInactiveOnDate(chore, weekStart)) {
      return false;
    }

    // Check weekPin (for bi-weekly chores)
    if (
      chore.interval.unit === 'week' &&
      chore.interval.n === 2 &&
      chore.weekPin
    ) {
      const currentWeek = this.dateService.getISOWeek(weekStart);
      const isOdd = currentWeek % 2 === 1;

      if (chore.weekPin === 'odd' && !isOdd) return false;
      if (chore.weekPin === 'even' && isOdd) return false;
    }

    // If lastAligned is pending, it's due
    if (chore.lastAligned === 'pending' || chore.lastAligned === null) {
      return chore.interval.unit === 'day'; // Only daily chores with null lastAligned
    }

    // Calculate next due date
    const dueDate = this.dateService.getNextDueDate(
      chore.lastAligned,
      chore.interval
    );
    if (!dueDate) return false;

    // Check if due date is within this week
    return this.dateService.isInWeek(dueDate, weekStart);
  }

  /**
   * Check if a chore is overdue as of today.
   * A chore is only overdue if it's past due AND outside its grace window (Rule 24).
   * Chores due this week or within grace window are not marked as overdue.
   */
  isOverdue(chore: Chore, weekStart?: Date): boolean {
    // Only chores that can be overdue are checked
    if (!chore.canBeOverdue) {
      return false;
    }

    if (!chore.lastAligned || chore.lastAligned === 'pending') {
      return false;
    }

    const dueDate = this.dateService.getNextDueDate(
      chore.lastAligned,
      chore.interval
    );
    if (!dueDate) return false;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // If due date is today or in the future, not overdue
    if (dueDate >= today) {
      return false;
    }

    // If within grace window, not overdue
    if (this.dateService.isWithinGraceWindow(dueDate, chore.interval)) {
      return false;
    }

    // Past due and outside grace window = overdue
    return true;
  }

  /**
   * Get all chores that are past due (due date before today, canBeOverdue true).
   * These are rendered in a dedicated "Past Due" section, not in weekly sections.
   */
  getPastDueChores(chores: Chore[]): Chore[] {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return chores.filter((chore) => {
      if (!chore.canBeOverdue) return false;
      const dueDate = this.dateService.getNextDueDate(chore.lastAligned, chore.interval);
      return dueDate !== null && dueDate < today;
    });
  }

  /**
   * Get the due date for a chore for display purposes.
   */
  getDueDate(chore: Chore): Date | null {
    return this.dateService.getNextDueDate(chore.lastAligned, chore.interval);
  }

  /**
   * Parse a MM-DD string to a Date (with given year).
   */
  private parseMMDD(mmdd: string, year: number): Date {
    const [month, day] = mmdd.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  /**
   * Format a Date as MM-DD.
   */
  private formatMMDD(date: Date): string {
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${month}-${day}`;
  }

  /**
   * Check if a date falls on a weekend (Saturday or Sunday).
   */
  private isWeekendDay(date: Date): boolean {
    const dayOfWeek = date.getDay();
    return dayOfWeek === 0 || dayOfWeek === 6; // 0 = Sunday, 6 = Saturday
  }

  /**
   * Group chores by section for the weekly checklist.
   */
  groupChoresForChecklist(
    chores: Chore[],
    weekStart: Date
  ): {
    daily: Chore[];
    thisWeek: Chore[];
    weekend: Chore[];
    onDeck: Chore[];
    inactive: Chore[];
  } {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const daily: Chore[] = [];
    const thisWeek: Chore[] = [];
    const weekend: Chore[] = [];
    const onDeck: Chore[] = [];
    const inactive: Chore[] = [];

    for (const chore of chores) {
      // Past-due chores (canBeOverdue + due date before today) are handled
      // in the dedicated "Past Due" section, not in weekly sections
      if (chore.canBeOverdue) {
        const dueDate = this.dateService.getNextDueDate(chore.lastAligned, chore.interval);
        if (dueDate && dueDate < today) continue;
      }

      // Check if inactive
      if (this.isInactiveOnDate(chore, weekStart)) {
        inactive.push(chore);
        continue;
      }

      // Daily chores
      if (chore.interval.unit === 'day' && chore.interval.n === 1) {
        daily.push(chore);
        continue;
      }

      // Check weekPin
      if (
        chore.interval.unit === 'week' &&
        chore.interval.n === 2 &&
        chore.weekPin
      ) {
        const currentWeek = this.dateService.getISOWeek(weekStart);
        const isOdd = currentWeek % 2 === 1;

        if (chore.weekPin === 'odd' && !isOdd) {
          onDeck.push(chore);
          continue;
        }
        if (chore.weekPin === 'even' && isOdd) {
          onDeck.push(chore);
          continue;
        }
      }

      // Determine due date
      const dueDate = this.dateService.getNextDueDate(
        chore.lastAligned,
        chore.interval
      );

      if (!dueDate) {
        // Pending chores go based on whether they're due on a weekend
        if (chore.lastAligned === 'pending') {
          thisWeek.push(chore); // Pending chores without due date go to thisWeek
        }
        continue;
      }

      // Check which section
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 6);
      const weekStartNorm = new Date(weekStart);
      weekStartNorm.setHours(0, 0, 0, 0);
      const isFutureWeek = weekStartNorm > today;

      // A chore appears only in the week where its due date falls
      if (this.dateService.isInWeek(dueDate, weekStart)) {
        // Due exactly this week — always show
        this.isWeekendDay(dueDate) ? weekend.push(chore) : thisWeek.push(chore);
      } else if (dueDate < weekStartNorm && !isFutureWeek) {
        // Overdue, but in current week — show as overdue, not on deck
        this.isWeekendDay(dueDate) ? weekend.push(chore) : thisWeek.push(chore);
      } else if (
        dueDate > weekEnd &&
        dueDate <= this.dateService.addDays(weekEnd, 14)
      ) {
        onDeck.push(chore);
      } else {
        onDeck.push(chore);
      }
    }

    return { daily, thisWeek, weekend, onDeck, inactive };
  }
}
