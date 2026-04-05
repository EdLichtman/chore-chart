import { Injectable } from '@angular/core';
import { Chore, DailyChore, ChoreData, CadenceEntry, Interval } from '../models/chore.model';
import { DateService } from './date.service';

export interface GroupedChecklist {
  daily: DailyChore[];
  categories: { key: string; label: string; chores: Chore[] }[];
  onDeck: Chore[];
}

@Injectable({
  providedIn: 'root',
})
export class ChecklistService {
  constructor(private dateService: DateService) {}

  getEffectiveInterval(chore: Chore, date: Date): Interval | null {
    if (this.isInactiveOnDate(chore, date)) {
      return null;
    }

    let effectiveInterval = chore.interval;
    let latestStart: Date | null = null;

    for (const entry of chore.annualCadence) {
      const entryDate = this.parseMMDD(entry.startDate, date.getFullYear());
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

  isInactiveOnDate(chore: Chore, date: Date): boolean {
    if (chore.annualCadence.length > 0) {
      const firstEntry = chore.annualCadence[0];
      const firstStartDate = this.parseMMDD(firstEntry.startDate, date.getFullYear());
      if (date < firstStartDate) {
        return true;
      }
    }

    for (const entry of chore.annualCadence) {
      if (entry.status === 'inactive') {
        const startDate = this.parseMMDD(entry.startDate, date.getFullYear());
        const nextEntry = this.getNextCadenceEntry(chore, entry);
        let endDate: Date | null = null;
        if (nextEntry) {
          endDate = this.parseMMDD(nextEntry.startDate, date.getFullYear());
        }
        if (date >= startDate && (!endDate || date < endDate)) {
          return true;
        }
      }
    }
    return false;
  }

  private getNextCadenceEntry(chore: Chore, current: CadenceEntry): CadenceEntry | null {
    const idx = chore.annualCadence.indexOf(current);
    if (idx >= 0 && idx < chore.annualCadence.length - 1) {
      return chore.annualCadence[idx + 1];
    }
    return null;
  }

  isPastDue(chore: Chore): boolean {
    if (!chore.canBeOverdue) return false;
    if (!chore.lastAligned || chore.lastAligned === 'pending') return false;
    const dueDate = this.dateService.getNextDueDate(chore.lastAligned ?? null, chore.interval);
    if (!dueDate) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return dueDate < today;
  }

  isOverdue(chore: Chore): boolean {
    if (!chore.canBeOverdue) return false;
    if (!chore.lastAligned || chore.lastAligned === 'pending') return false;

    const dueDate = this.dateService.getNextDueDate(chore.lastAligned ?? null, chore.interval);
    if (!dueDate) return false;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (dueDate >= today) return false;
    if (this.dateService.isWithinGraceWindow(dueDate, chore.interval)) return false;

    return true;
  }

  getDueDate(chore: Chore): Date | null {
    return this.dateService.getNextDueDate(chore.lastAligned ?? null, chore.interval);
  }

  private getIntervalDays(interval: Interval): number {
    switch (interval.unit) {
      case 'day':   return interval.n;
      case 'week':  return interval.n * 7;
      case 'month': return interval.n * 30;
      case 'year':  return interval.n * 365;
    }
  }

  private parseMMDD(mmdd: string, year: number): Date {
    const [month, day] = mmdd.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  private formatMMDD(date: Date): string {
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${month}-${day}`;
  }

  groupChoresForChecklist(choreData: ChoreData, weekStart: Date): GroupedChecklist {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const weekStartNorm = new Date(weekStart);
    weekStartNorm.setHours(0, 0, 0, 0);

    const currentAnchor = this.dateService.getWeekAnchor(today);
    currentAnchor.setHours(0, 0, 0, 0);
    const isFutureWeek = weekStartNorm > currentAnchor;

    const onDeck: Chore[] = [];
    const categories: { key: string; label: string; chores: Chore[] }[] = [];

    for (const [key, category] of Object.entries(choreData.categories)) {
      const dueChores: Chore[] = [];

      for (const chore of category.chores) {
        if (this.isInactiveOnDate(chore, weekStart)) continue;

        // weekPin — bi-weekly chores that don't match this week
        if (chore.interval.unit === 'week' && chore.interval.n === 2 && chore.weekPin) {
          const currentWeek = this.dateService.getISOWeek(weekStart);
          const isOdd = currentWeek % 2 === 1;
          if (chore.weekPin === 'odd' && !isOdd) { onDeck.push(chore); continue; }
          if (chore.weekPin === 'even' && isOdd) { onDeck.push(chore); continue; }
        }

        // Pending chores always show
        if (!chore.lastAligned || chore.lastAligned === 'pending') {
          dueChores.push(chore);
          continue;
        }

        const dueDate = this.dateService.getNextDueDate(chore.lastAligned ?? null, chore.interval);
        if (!dueDate) continue;

        if (isFutureWeek) {
          // Future weeks: project the due date forward by the interval until it
          // reaches this week, then check if it lands here.
          const intervalDays = this.getIntervalDays(chore.interval);
          let projectedDue = new Date(dueDate);
          while (projectedDue < weekStartNorm) {
            projectedDue = this.dateService.addDays(projectedDue, intervalDays);
          }
          if (this.dateService.isInWeek(projectedDue, weekStart)) {
            dueChores.push(chore);
          }
        } else {
          // Current week: show due this week + anything overdue
          if (this.dateService.isInWeek(dueDate, weekStart) || dueDate < weekStartNorm) {
            dueChores.push(chore);
          } else {
            onDeck.push(chore);
          }
        }
      }

      categories.push({ key, label: category.label, chores: dueChores });
    }

    return { daily: choreData.daily ?? [], categories, onDeck };
  }
}
