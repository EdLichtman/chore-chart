import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DateService } from '../../services/date.service';

@Component({
  selector: 'app-controls',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './controls.component.html',
  styleUrls: ['./controls.component.scss'],
})
export class ControlsComponent {
  @Input() currentWeekStart!: Date;
  @Input() viewMode: '1week' | '4weeks' = '1week';
  @Output() weekChanged = new EventEmitter<Date>();
  @Output() viewModeChanged = new EventEmitter<'1week' | '4weeks'>();
  @Output() export = new EventEmitter<void>();

  constructor(private dateService: DateService) {}

  previousWeek(): void {
    const prev = this.dateService.addDays(this.currentWeekStart, -7);
    this.weekChanged.emit(prev);
  }

  nextWeek(): void {
    const next = this.dateService.addDays(this.currentWeekStart, 7);
    this.weekChanged.emit(next);
  }

  exportChores(): void {
    this.export.emit();
  }

  printPage(): void {
    window.print();
  }

  toggleViewMode(): void {
    const newMode = this.viewMode === '1week' ? '4weeks' : '1week';
    this.viewModeChanged.emit(newMode);
  }
}
