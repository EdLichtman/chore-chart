import { Injectable } from '@angular/core';
import { Interval } from '../models/chore.model';

@Injectable({
  providedIn: 'root',
})
export class DateService {
  /**
   * Calculate the Sunday (week anchor) for a given date.
   * Uses Wed/Thu boundary: Sun-Wed is current week, Thu-Sat is next week.
   */
  getWeekAnchor(date: Date = new Date()): Date {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    const dayOfWeek = d.getDay(); // 0 = Sun, 6 = Sat

    // If it's Sun-Wed (0-3), anchor to this Sunday
    // If it's Thu-Sat (4-6), anchor to next Sunday
    let daysToSubtract;
    if (dayOfWeek >= 0 && dayOfWeek <= 3) {
      daysToSubtract = dayOfWeek;
    } else {
      daysToSubtract = dayOfWeek - 7;
    }

    const anchor = new Date(d);
    anchor.setDate(anchor.getDate() - daysToSubtract);
    return anchor;
  }

  /**
   * Get ISO week number (1-52).
   */
  getISOWeek(date: Date = new Date()): number {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + 4 - (d.getDay() || 7));
    const yearStart = new Date(d.getFullYear(), 0, 1);
    return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  }

  /**
   * Add days to a date.
   */
  addDays(date: Date, days: number): Date {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
  }

  /**
   * Calculate the next due date for a chore based on lastAligned and interval.
   */
  getNextDueDate(lastAligned: string | null | 'pending', interval: Interval): Date | null {
    if (!lastAligned || lastAligned === 'pending') {
      return null;
    }

    const lastAlignedDate = new Date(lastAligned);
    lastAlignedDate.setHours(0, 0, 0, 0);

    let daysToAdd = 0;
    switch (interval.unit) {
      case 'day':
        daysToAdd = interval.n;
        break;
      case 'week':
        daysToAdd = interval.n * 7;
        break;
      case 'month':
        daysToAdd = interval.n * 30; // Rough estimate
        break;
      case 'year':
        daysToAdd = interval.n * 365;
        break;
    }

    return this.addDays(lastAlignedDate, daysToAdd);
  }

  /**
   * Format a date as YYYY-MM-DD.
   */
  formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  /**
   * Format a date for display (e.g., "Sunday, April 5, 2026").
   */
  formatDateDisplay(date: Date): string {
    const options: Intl.DateTimeFormatOptions = {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    };
    return date.toLocaleDateString('en-US', options);
  }

  /**
   * Check if a date is within the given week (Sunday to Saturday).
   */
  isInWeek(date: Date, weekStart: Date): boolean {
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekEnd.getDate() + 6);

    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    weekStart.setHours(0, 0, 0, 0);
    weekEnd.setHours(0, 0, 0, 0);

    return d >= weekStart && d <= weekEnd;
  }

  /**
   * Check if today is before the week start.
   */
  isTodayBeforeWeek(weekStart: Date): boolean {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const ws = new Date(weekStart);
    ws.setHours(0, 0, 0, 0);
    return today < ws;
  }

  /**
   * Get the grace window (in days) for a chore interval.
   * Grace window is the period during which a chore can be completed early/late
   * without drifting the next due date (Rule 24).
   */
  getGraceWindowDays(interval: Interval): number {
    return interval.unit === 'year' ? 14 : 7;
  }

  /**
   * Check if today falls within the grace window of a due date.
   * If true, the chore is not yet overdue.
   */
  isWithinGraceWindow(dueDate: Date, interval: Interval): boolean {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const graceDays = this.getGraceWindowDays(interval);
    const graceEnd = this.addDays(dueDate, graceDays);
    return today <= graceEnd;
  }
}
