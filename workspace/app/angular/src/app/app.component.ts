import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { ChoreDataService } from './services/chore-data.service';
import { DateService } from './services/date.service';
import { ChecklistService } from './services/checklist.service';
import { Chore } from './models/chore.model';
import { ImportComponent } from './components/import/import.component';
import { ChecklistComponent } from './components/checklist/checklist.component';
import { ControlsComponent } from './components/controls/controls.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, ImportComponent, ChecklistComponent, ControlsComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  chores$ = this.choreDataService.getChores();
  fileName$ = this.choreDataService.getFileName();
  hasChores = false;
  pastDueChores: Chore[] = [];
  currentWeekStart: Date = new Date();
  weekDisplay: string = '';
  viewMode: '1week' | '4weeks' = '1week';

  constructor(
    private choreDataService: ChoreDataService,
    public dateService: DateService,
    private checklistService: ChecklistService
  ) {
    this.updateWeekDisplay();
  }

  ngOnInit(): void {
    // Snap to the start of the week (Sunday)
    this.currentWeekStart = this.dateService.getWeekAnchor(this.currentWeekStart);
    this.updateWeekDisplay();

    this.chores$.subscribe((chores) => {
      this.hasChores = chores.length > 0;
      this.pastDueChores = this.checklistService.getPastDueChores(chores);
    });
  }

  onFileImported(): void {
    this.updateWeekDisplay();
  }

  onWeekChanged(weekStart: Date): void {
    this.currentWeekStart = weekStart;
    this.updateWeekDisplay();
  }

  private updateWeekDisplay(): void {
    this.weekDisplay = `${this.dateService.formatDateDisplay(
      this.currentWeekStart
    )} — ISO Week ${this.dateService.getISOWeek(this.currentWeekStart)} (${
      this.dateService.getISOWeek(this.currentWeekStart) % 2 === 1
        ? 'odd'
        : 'even'
    })`;
  }

  get weekStarts(): Date[] {
    if (this.viewMode === '4weeks') {
      return [0, 7, 14, 21].map((offset) =>
        this.dateService.addDays(this.currentWeekStart, offset)
      );
    }
    return [this.currentWeekStart];
  }

  onViewModeChanged(mode: '1week' | '4weeks'): void {
    this.viewMode = mode;
  }

  exportChores(): void {
    this.choreDataService.exportChores();
  }
}
