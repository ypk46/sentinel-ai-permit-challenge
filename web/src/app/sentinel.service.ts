import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '../environments/environment.development';

export interface Response<T> {
  data: T;
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  key: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
}

export interface Document {
  id: number;
  content: string;
  title: string;
  key: string;
  sensitivity: string;
}

@Injectable({
  providedIn: 'root',
})
export class SentinelService {
  private http = inject(HttpClient);

  constructor() {}

  /**
   * Retrieves the list of users from the Sentinel API.
   * @returns An observable containing the response with user data.
   */
  getUsers() {
    return this.http.get<Response<User[]>>(`${environment.apiUrl}/users`);
  }

  /**
   * Retrieves the list of documents for a specific user.
   * @param userKey - The key of the user whose documents are to be retrieved.
   * @returns An observable containing the response with document data.
   */
  getDocuments(userKey: string) {
    return this.http.get<Document[]>(`${environment.apiUrl}/documents`, {
      params: { user_key: userKey },
    });
  }
}
