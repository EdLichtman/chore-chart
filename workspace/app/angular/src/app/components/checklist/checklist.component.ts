import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chore } from '../../models/chore.model';
import { ChecklistService } from '../../services/checklist.service';
import { DateService } from '../../services/date.service';

interface ChecklistData {
  daily: Chore[];
  thisWeek: Chore[];
  weekend: Chore[];
  onDeck: Chore[];
  inactive: Chore[];
}

@Component({
  selector: 'app-checklist',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './checklist.component.html',
  styleUrls: ['./checklist.component.scss'],
})
export class ChecklistComponent implements OnInit {
  @Input() chores: Chore[] | null = [];
  @Input() weekStart: Date = new Date();
  @Input() isMultiWeekView: boolean = false;

  checklistData: ChecklistData = {
    daily: [],
    thisWeek: [],
    weekend: [],
    onDeck: [],
    inactive: [],
  };

  weekDays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  checkboxState: Map<string, boolean[]> = new Map(); // For daily chore checkboxes

  constructor(
    private checklistService: ChecklistService,
    private dateService: DateService
  ) {}

  ngOnInit(): void {
    this.updateChecklist();
  }

  ngOnChanges(): void {
    this.updateChecklist();
  }

  private updateChecklist(): void {
    if (!this.chores) return;

    this.checklistData = this.checklistService.groupChoresForChecklist(
      this.chores,
      this.weekStart
    );

    // Initialize checkbox state for daily chores (7 days)
    for (const chore of this.checklistData.daily) {
      if (!this.checkboxState.has(chore.id)) {
        this.checkboxState.set(chore.id, Array(7).fill(false));
      }
    }
  }

  isOverdue(chore: Chore, weekStart?: Date): boolean {
    return this.checklistService.isOverdue(chore, weekStart);
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
