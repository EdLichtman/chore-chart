import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { ChoreData } from '../models/chore.model';

@Injectable({
  providedIn: 'root',
})
export class ChoreDataService {
  private choreData$ = new BehaviorSubject<ChoreData | null>(null);
  private fileName$ = new BehaviorSubject<string>('');

  constructor() {}

  loadFromFile(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const content = event.target?.result as string;
          const parsed = JSON.parse(content);

          if (!parsed.categories || typeof parsed.categories !== 'object') {
            throw new Error('Invalid chore file: missing categories object');
          }
          if (!parsed.gridProperties) {
            throw new Error('Invalid chore file: missing gridProperties');
          }

          this.choreData$.next(parsed as ChoreData);
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

  getChoreData(): Observable<ChoreData | null> {
    return this.choreData$.asObservable();
  }

  getCurrentChoreData(): ChoreData | null {
    return this.choreData$.value;
  }

  getFileName(): Observable<string> {
    return this.fileName$.asObservable();
  }

  exportChores(): void {
    const data = this.choreData$.value;
    if (!data) return;
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = this.fileName$.value || 'chores.json';
    link.click();
    URL.revokeObjectURL(url);
  }

  hasChores(): boolean {
    const data = this.choreData$.value;
    if (!data) return false;
    return Object.values(data.categories).some(cat => cat.chores.length > 0);
  }
}
