import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Chore, ChoreFile } from '../models/chore.model';

@Injectable({
  providedIn: 'root',
})
export class ChoreDataService {
  private chores$ = new BehaviorSubject<Chore[]>([]);
  private fileName$ = new BehaviorSubject<string>('');

  constructor() {}

  /**
   * Load chores from a file object.
   */
  loadFromFile(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const content = event.target?.result as string;
          const choreFile: ChoreFile = JSON.parse(content);

          // Validate schema
          if (!Array.isArray(choreFile.chores)) {
            throw new Error('Invalid chore file: missing chores array');
          }

          this.chores$.next(choreFile.chores);
          this.fileName$.next(file.name);
          resolve();
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsText(file);
    });
  }

  /**
   * Get all loaded chores as an observable.
   */
  getChores(): Observable<Chore[]> {
    return this.chores$.asObservable();
  }

  /**
   * Get current chores synchronously.
   */
  getCurrentChores(): Chore[] {
    return this.chores$.value;
  }

  /**
   * Get the loaded file name.
   */
  getFileName(): Observable<string> {
    return this.fileName$.asObservable();
  }

  /**
   * Export current chores as JSON file download.
   */
  exportChores(): void {
    const chores = this.chores$.value;
    const choreFile: ChoreFile = { chores };
    const json = JSON.stringify(choreFile, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = this.fileName$.value || 'chores.json';
    link.click();
    URL.revokeObjectURL(url);
  }

  /**
   * Clear loaded chores.
   */
  clear(): void {
    this.chores$.next([]);
    this.fileName$.next('');
  }

  /**
   * Check if chores are loaded.
   */
  hasChores(): boolean {
    return this.chores$.value.length > 0;
  }
}
