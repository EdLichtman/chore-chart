import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chore, DailyChore, ChoreData } from '../../models/chore.model';
import { ChecklistService, GroupedChecklist } from '../../services/checklist.service';
import { DateService } from '../../services/date.service';

@Component({
  selector: 'app-checklist',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './checklist.component.html',
  styleUrls: ['./checklist.component.scss'],
})
export class ChecklistComponent implements OnChanges {
  @Input() choreData: ChoreData | null = null;
  @Input() weekStart: Date = new Date();
  @Input() isMultiWeekView: boolean = false;

  checklistData: GroupedChecklist = {
    daily: [],
    categories: [],
    onDeck: [],
  };

  weekDays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  checkboxState: Map<string, boolean[]> = new Map();

  constructor(
    private checklistService: ChecklistService,
    private dateService: DateService
  ) {}

  ngOnChanges(): void {
    if (!this.choreData) return;
    this.checklistData = this.checklistService.groupChoresForChecklist(
      this.choreData,
      this.weekStart
    );
    for (const chore of this.checklistData.daily) {
      if (!this.checkboxState.has(chore.id)) {
        this.checkboxState.set(chore.id, Array(7).fill(false));
      }
    }
  }

  get isCurrentOrPastWeek(): boolean {
    const anchor = this.dateService.getWeekAnchor(new Date());
    anchor.setHours(0, 0, 0, 0);
    const ws = new Date(this.weekStart);
    ws.setHours(0, 0, 0, 0);
    return ws <= anchor;
  }

  get categoryColClass(): string {
    const webCols = this.choreData?.gridProperties.web.columns;
    const n = webCols === 'auto' || webCols == null
      ? (() => {
          const count = this.checklistData.categories.length;
          return count <= 3 ? count : Math.ceil(Math.sqrt(count));
        })()
      : (webCols as number);
    const bs = Math.floor(12 / n);
    return `col-12 col-md-${bs}`;
  }

  get printColumns(): number {
    const cols = this.choreData?.gridProperties.print.columns;
    if (cols === 'auto' || cols == null) {
      const count = this.checklistData.categories.length;
      return count <= 3 ? count : Math.ceil(Math.sqrt(count));
    }
    return cols as number;
  }

  isOverdue(chore: Chore): boolean {
    return this.checklistService.isOverdue(chore);
  }

  isPastDue(chore: Chore): boolean {
    return this.checklistService.isPastDue(chore);
  }

  isPending(chore: Chore): boolean {
    return chore.lastAligned === 'pending';
  }

  getLastAlignedDisplay(chore: Chore): string | null {
    if (!chore.lastAligned || chore.lastAligned === 'pending') return null;
    const date = new Date(chore.lastAligned);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  getDueDate(chore: Chore): Date | null {
    return this.checklistService.getDueDate(chore);
  }

  formatDate(date: Date): string {
    return this.dateService.formatDate(date);
  }

  getDailyCheckboxes(choreId: string): boolean[] {
    return this.checkboxState.get(choreId) || Array(7).fill(false);
  }

  toggleDailyCheckbox(choreId: string, dayIndex: number): void {
    const checkboxes = this.checkboxState.get(choreId);
    if (checkboxes) {
      checkboxes[dayIndex] = !checkboxes[dayIndex];
    }
  }
}
