import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChoreDataService } from '../../services/chore-data.service';

@Component({
  selector: 'app-import',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './import.component.html',
  styleUrls: ['./import.component.scss'],
})
export class ImportComponent {
  @Output() fileImported = new EventEmitter<void>();

  isLoading = false;
  errorMessage = '';
  dragActive = false;

  constructor(private choreDataService: ChoreDataService) {}

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragActive = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragActive = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragActive = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  private handleFile(file: File): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.choreDataService
      .loadFromFile(file)
      .then(() => {
        this.isLoading = false;
        this.fileImported.emit();
      })
      .catch((error) => {
        this.isLoading = false;
        this.errorMessage = `Error loading file: ${error.message}`;
      });
  }
}
