import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChoreDataService } from './services/chore-data.service';
import { DateService } from './services/date.service';
import { ImportComponent } from './components/import/import.component';
import { ChecklistComponent } from './components/checklist/checklist.component';
import { ControlsComponent } from './components/controls/controls.component';
import { RequirementsComponent } from './components/requirements/requirements.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ImportComponent, ChecklistComponent, ControlsComponent, RequirementsComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  choreData$ = this.choreDataService.getChoreData();
  fileName$ = this.choreDataService.getFileName();
  hasChores = false;
  currentWeekStart: Date = new Date();
  viewMode: '1week' | '4weeks' = '1week';

  constructor(
    private choreDataService: ChoreDataService,
    public dateService: DateService
  ) {}

  ngOnInit(): void {
    this.currentWeekStart = this.dateService.getWeekAnchor(this.currentWeekStart);

    this.choreData$.subscribe((data) => {
      this.hasChores = data !== null && Object.values(data.categories).some(c => c.chores.length > 0);
    });
  }

  onFileImported(): void {}

  onWeekChanged(weekStart: Date): void {
    this.currentWeekStart = weekStart;
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
