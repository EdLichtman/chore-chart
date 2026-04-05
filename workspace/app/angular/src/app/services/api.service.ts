import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Chore, ChoreFile } from '../models/chore.model';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Import a chore file and generate a PDF.
   * Returns the PDF file as a blob.
   */
  importAndGeneratePDF(chores: Chore[]): Observable<Blob> {
    const choreFile: ChoreFile = { chores };

    return this.http.post(`${this.apiUrl}/chores/import`, choreFile, {
      responseType: 'blob',
    });
  }

  /**
   * Validate a chore file against the schema.
   */
  validateChores(chores: Chore[]): Observable<{ valid: boolean; count?: number }> {
    const choreFile: ChoreFile = { chores };
    return this.http.post<{ valid: boolean; count?: number }>(
      `${this.apiUrl}/chores/validate`,
      choreFile
    );
  }

  /**
   * Health check.
   */
  health(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(`${this.apiUrl}/health`);
  }
}
