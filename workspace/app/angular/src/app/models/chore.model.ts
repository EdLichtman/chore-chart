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
  dayConfigurable: boolean;
  weekPin: 'odd' | 'even' | null;
  dayPin: 1 | 15 | null;
  lastAligned?: string | 'pending' | null;
  notes: string[];
  requirements: Requirement[];
  annualCadence: CadenceEntry[];
  canBeOverdue: boolean;
}

export interface DailyChore {
  id: string;
  name: string;
  notes: string[];
}

export interface ChoreCategory {
  label: string;
  chores: Chore[];
}

export interface GridDimensions {
  columns: number | 'auto';
  rows: number | 'auto';
}

export interface GridProperties {
  print: GridDimensions;
  web: GridDimensions;
}

export interface ChoreData {
  gridProperties: GridProperties;
  daily: DailyChore[];
  categories: Record<string, ChoreCategory>;
}
