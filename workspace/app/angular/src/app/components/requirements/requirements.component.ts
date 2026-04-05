import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChoreData, Chore } from '../../models/chore.model';
import { ChecklistService } from '../../services/checklist.service';

@Component({
  selector: 'app-requirements',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './requirements.component.html',
  styleUrls: ['./requirements.component.scss'],
})
export class RequirementsComponent {
  @Input() choreData: ChoreData | null = null;
  @Input() weekStarts: Date[] = [];

  constructor(private checklistService: ChecklistService) {}

  get filteredCategories(): { key: string; label: string; chores: Chore[] }[] {
    if (!this.choreData) return [];
    return Object.entries(this.choreData.categories)
      .map(([key, cat]) => ({
        key,
        label: cat.label,
        chores: cat.chores.filter(c =>
          c.requirements.length > 0 &&
          this.weekStarts.some(ws => !this.checklistService.isInactiveOnDate(c, ws))
        ),
      }))
      .filter(cat => cat.chores.length > 0);
  }

  get printColumns(): number {
    const cols = this.choreData?.gridProperties.print.columns;
    if (cols === 'auto' || cols == null) return 2;
    return cols as number;
  }

  get categoryColClass(): string {
    const webCols = this.choreData?.gridProperties.web.columns;
    const n = webCols === 'auto' || webCols == null ? 2 : (webCols as number);
    return `col-12 col-md-${Math.floor(12 / n)}`;
  }
}
