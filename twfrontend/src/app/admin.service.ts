import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

export interface AdminUser {
  readonly id: string;
  readonly name: string;
  readonly email: string;
  readonly role: string;
  readonly created_at: string;
}

export interface AdminUserCreate {
  readonly name: string;
  readonly email: string;
  readonly password: string;
  readonly role: string;
}

export interface AdminUserUpdate {
  readonly name?: string;
  readonly role?: string;
  readonly password?: string;
}

export interface StockListProviderConfig {
  readonly id: string;
  readonly provider: string;
  readonly display_name: string;
  readonly api_key: string | null;
  readonly base_url: string | null;
  readonly is_active: boolean;
  readonly is_default: boolean;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface StockListProviderUpsert {
  readonly provider: string;
  readonly display_name: string;
  readonly api_key?: string | null;
  readonly base_url?: string | null;
  readonly is_active: boolean;
  readonly is_default: boolean;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly http = inject(HttpClient);

  listUsers(): Observable<AdminUser[]> {
    return this.http.get<AdminUser[]>(`${environment.apiBaseUrl}/admin/users`);
  }

  createUser(payload: AdminUserCreate): Observable<AdminUser> {
    return this.http.post<AdminUser>(`${environment.apiBaseUrl}/admin/users`, payload);
  }

  updateUser(userId: string, payload: AdminUserUpdate): Observable<AdminUser> {
    return this.http.patch<AdminUser>(`${environment.apiBaseUrl}/admin/users/${userId}`, payload);
  }

  deleteUser(userId: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBaseUrl}/admin/users/${userId}`);
  }

  listProviders(): Observable<StockListProviderConfig[]> {
    return this.http.get<StockListProviderConfig[]>(`${environment.apiBaseUrl}/admin/providers`);
  }

  createProvider(payload: StockListProviderUpsert): Observable<StockListProviderConfig> {
    return this.http.post<StockListProviderConfig>(`${environment.apiBaseUrl}/admin/providers`, payload);
  }

  updateProvider(providerId: string, payload: StockListProviderUpsert): Observable<StockListProviderConfig> {
    return this.http.patch<StockListProviderConfig>(
      `${environment.apiBaseUrl}/admin/providers/${providerId}`,
      payload
    );
  }
}
