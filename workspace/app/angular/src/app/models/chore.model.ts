export interface Interval {
  n: number;
  unit: 'day' | 'week' | 'month' | 'year';
}

export interface Requirement {
  id: string;
  name: string;
  interval: Interval;
  lastAligned: string | null;
}

export interface CadenceEntry {
  startDate: string; // MM-DD format
  interval?: Interval;
  status?: 'inactive';
}

export interface Chore {
  id: string;
  name: string;
  interval: Interval;
  weekend: boolean;
  dayConfigurable: boolean;
  weekPin: 'odd' | 'even' | null;
  dayPin: 1 | 15 | null;
  lastAligned: string | 'pending' | null;
  notes: string[];
  synchronizedWith: string[];
  requirements: Requirement[];
  annualCadence: CadenceEntry[];
  canBeOverdue: boolean; // false for daily/weekly/bi-weekly, true for monthly+
}

export interface ChoreFile {
  chores: Chore[];
}

export interface ChecklistChore extends Chore {
  dueDate: Date;
  isOverdue: boolean;
  isUpcoming: boolean;
}
